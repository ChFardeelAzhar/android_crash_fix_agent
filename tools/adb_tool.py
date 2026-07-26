import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class ADBInput(BaseModel):
    command_type: str = Field(
        ...,
        description="The ADB operation to execute. Allowed: 'list_devices', 'launch_app', 'screencap', 'screenrecord_start', 'screenrecord_stop', 'screen_record_start', 'screen_record_stop_and_pull', 'get_logcat', 'input_tap', 'input_text', 'input_keyevent'"
    )
    package_name: str = Field(
        default="com.ananinja.tms",
        description="The target Android application package ID."
    )
    activity_name: str = Field(
        default="",
        description="Optional activity class name to start (e.g. '.ui.MainActivity')."
    )
    filename: str = Field(
        default="",
        description="Target output filename inside output/ (e.g. 'screenshot.png' or 'reproduction.mp4')."
    )
    x: int = Field(
        default=0,
        description="X coordinate for input_tap."
    )
    y: int = Field(
        default=0,
        description="Y coordinate for input_tap."
    )
    text_content: str = Field(
        default="",
        description="Text content to type for input_text."
    )
    key_code: int = Field(
        default=0,
        description="Key code for input_keyevent (e.g., 4 for BACK)."
    )

class ADBTool(BaseTool):
    name: str = "adb_tool"
    description: str = (
        "Interacts with connected Android devices or emulators using ADB. "
        "Allows listing devices, launching apps, getting logcat dumps, taking screenshots, and recording video. "
        "All outputs are saved to the output/ directory. Operates securely through parameterized inputs."
    )
    args_schema: Type[BaseModel] = ADBInput

    def _get_adb_path(self) -> str:
        # Search PATH
        adb_path = shutil.which("adb")
        if adb_path:
            return adb_path

        # Check standard Mac Android SDK path
        home_dir = Path.home()
        mac_adb = home_dir / "Library/Android/sdk/platform-tools/adb"
        if mac_adb.is_file():
            return str(mac_adb)

        # Default fallback
        return "adb"

    def _sanitize_input(self, val: str) -> bool:
        if not val:
            return True
        # Reject shell escape characters
        return not any(char in val for char in [";", "|", "&", "$", "`", "<", ">", "\n", "\r"])

    def _has_connected_devices(self, adb_exec: str) -> bool:
        try:
            res = subprocess.run([adb_exec, "devices"], capture_output=True, text=True, timeout=5)
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            # First line is "List of devices attached"
            return len(lines) > 1 and any("device" in line for line in lines[1:])
        except Exception:
            return False

    def _run(self, command_type: str, package_name: str = "com.ananinja.tms", activity_name: str = "", filename: str = "", x: int = 0, y: int = 0, text_content: str = "", key_code: int = 0) -> str:
        adb_exec = self._get_adb_path()

        # Sanitize inputs
        if not (self._sanitize_input(package_name) and self._sanitize_input(activity_name) and self._sanitize_input(filename)):
            return "Security Error: Input contains invalid shell characters."

        # Verify device connection for active commands
        if command_type != "list_devices" and not self._has_connected_devices(adb_exec):
            return "Error: No connected Android devices or emulators found. Please start an emulator or connect a device before executing this command."

        # Ensure output directory exists
        output_dir = Path("output").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if command_type == "list_devices":
            try:
                res = subprocess.run([adb_exec, "devices"], capture_output=True, text=True, timeout=10)
                return f"Connected devices:\n{res.stdout}"
            except Exception as e:
                return f"Error listing devices: {str(e)}"

        elif command_type == "launch_app":
            try:
                if activity_name:
                    # Launch specific activity
                    target = f"{package_name}/{activity_name}"
                    cmd = [adb_exec, "shell", "am", "start", "-n", target]
                else:
                    # Launch using monkey tool (launches the launcher activity automatically)
                    cmd = [adb_exec, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]

                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return f"Launch app output:\nStdout: {res.stdout}\nStderr: {res.stderr}"
            except Exception as e:
                return f"Error launching app: {str(e)}"

        elif command_type == "screencap":
            fname = filename if filename else "screenshot.png"
            if not fname.endswith(".png"):
                fname += ".png"
            target_path = output_dir / fname

            try:
                # Capture on device
                subprocess.run([adb_exec, "shell", "screencap", "-p", "/sdcard/screenshot.png"], check=True, timeout=15)
                # Pull to output/
                subprocess.run([adb_exec, "pull", "/sdcard/screenshot.png", str(target_path)], check=True, timeout=15)
                # Cleanup on device
                subprocess.run([adb_exec, "shell", "rm", "/sdcard/screenshot.png"], timeout=10)
                return f"Success: Screenshot saved to output/{fname}"
            except subprocess.CalledProcessError as e:
                return f"Error capturing screen: {e.stderr}"
            except Exception as e:
                return f"Error capturing screen: {str(e)}"

        elif command_type in ("screenrecord_start", "screen_record_start"):
            try:
                # Terminate any existing screenrecordings on the device first
                subprocess.run([adb_exec, "shell", "pkill", "-2", "screenrecord"], timeout=10)
                time.sleep(1)

                # Start screenrecord in the background
                # We limit size to keep file size small
                cmd = [adb_exec, "shell", "screenrecord", "--size", "720x1280", "/sdcard/record.mp4"]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Success: Screen recording started in the background on the device."
            except Exception as e:
                return f"Error starting screen record: {str(e)}"

        elif command_type in ("screenrecord_stop", "screen_record_stop_and_pull"):
            fname = filename if filename else "reproduction.mp4"
            if not fname.endswith(".mp4"):
                fname += ".mp4"
            target_path = output_dir / fname

            try:
                # Stop on-device screenrecord cleanly by sending SIGINT (2)
                subprocess.run([adb_exec, "shell", "pkill", "-2", "screenrecord"], check=True, timeout=10)
                # Wait 2 seconds for container header finalizing
                time.sleep(2)
                # Pull video to output/
                subprocess.run([adb_exec, "pull", "/sdcard/record.mp4", str(target_path)], check=True, timeout=20)
                # Cleanup on device
                subprocess.run([adb_exec, "shell", "rm", "/sdcard/record.mp4"], timeout=10)
                if command_type == "screen_record_stop_and_pull":
                    return str(target_path)
                return f"Success: Screen recording saved to output/{fname}"
            except subprocess.CalledProcessError as e:
                return f"Error stopping/pulling recording: {e.stderr}"
            except Exception as e:
                return f"Error stopping/pulling recording: {str(e)}"

        elif command_type == "get_logcat":
            try:
                # Get last 200 lines of logcat with level Warning or Error, or containing package name
                cmd = [adb_exec, "logcat", "-d", "-t", "200"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                # Filter lines matching package name or exception trace
                filtered_lines = []
                for line in res.stdout.splitlines():
                    if package_name in line or "Exception" in line or "FATAL" in line or "Error" in line:
                        filtered_lines.append(line)
                
                if not filtered_lines:
                    # Fallback to last 100 raw lines
                    filtered_lines = res.stdout.splitlines()[-100:]

                return "Logcat log output:\n" + "\n".join(filtered_lines)
            except Exception as e:
                return f"Error reading logcat: {str(e)}"

        elif command_type == "input_tap":
            try:
                cmd = [adb_exec, "shell", "input", "tap", str(x), str(y)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return f"Success: Tapped on coordinates ({x}, {y}). Output: {res.stdout}"
            except Exception as e:
                return f"Error executing input_tap: {str(e)}"

        elif command_type == "input_text":
            try:
                sanitized_text = text_content.replace(" ", "%s")
                cmd = [adb_exec, "shell", "input", "text", sanitized_text]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return f"Success: Typed text. Output: {res.stdout}"
            except Exception as e:
                return f"Error executing input_text: {str(e)}"

        elif command_type == "input_keyevent":
            try:
                cmd = [adb_exec, "shell", "input", "keyevent", str(key_code)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return f"Success: Sent key event {key_code}. Output: {res.stdout}"
            except Exception as e:
                return f"Error executing key event: {str(e)}"

        else:
            return f"Error: Unknown command_type '{command_type}'."
