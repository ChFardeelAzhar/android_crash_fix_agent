import os
import sys
import re
import subprocess
import gradio as gr

def parse_subprocess_log(full_log):
    # Initialize default state
    task_statuses = ["Pending"] * 8
    
    # Task mapping inside crew.jsonc
    task_mapping = {
        "ticket_intake_task": 0,
        "ticket_analysis_task": 1,
        "prompt_engineering_task": 2,
        "antigravity_execution_task": 3,
        "build_verification_task": 4,
        "device_verification_task": 5,
        "git_release_task": 6,
        "final_report_task": 7
    }
    
    # Find started tasks
    started = re.findall(r"(?:Task Started:?\s*|Name:\s*)(\w+_task)", full_log)
    for t_name in started:
        if t_name in task_mapping:
            idx = task_mapping[t_name]
            task_statuses[idx] = "Running"
            # Set preceding tasks as completed
            for i in range(idx):
                if task_statuses[i] in ("Pending", "Running"):
                    task_statuses[i] = "Completed"
                    
    # Find completed tasks
    completed = re.findall(r"(?:Task Completed:?\s*|Name:\s*)(\w+_task)", full_log)
    for t_name in completed:
        if t_name in task_mapping:
            idx = task_mapping[t_name]
            task_statuses[idx] = "Completed"

    # Identify currently active agent
    current_agent = "System Router"
    agents = re.findall(r"Agent:\s*([^\n\r]+)", full_log)
    if agents:
        current_agent = agents[-1].strip()
        
    agent_goals = {
        "System Router": "Awaiting kickoff...",
        "Engineering Intake Specialist": "Communicating with ticket APIs to retrieve raw contexts.",
        "Android Ticket Analyst": "Analyzing logs/issues and classifying them into Fix, Feature, or Chore.",
        "Senior Android Engineering Lead": "Drafting precise code modification prompts for autonomous agents.",
        "Android Antigravity Operator": "Applying file changes safely via Antigravity CLI ('agy').",
        "Android Build Verifier": "Compiling project changes and running unit test checks via Gradle.",
        "Android Device QA Specialist": "Performing UI checks, tapping elements, and capturing screen logs/recordings.",
        "Android Git Release Manager": "Verifying naming policies, creating branches, and committing changed files.",
        "Android PR Report Compiler": "Consolidating E2E phase results into a clean, final pull request report."
    }
    current_agent_goal = agent_goals.get(current_agent, "Processing active pipeline operations...")
    
    # Calculate simple stats
    completed_count = task_statuses.count("Completed")
    progress_percentage = int((completed_count / 8.0) * 100)
    
    # Generate HTML task list as horizontal large circles (size: 46px)
    labels = ["Ingest", "Analyze", "Brief", "Fix", "Compile", "QA", "Release", "Report"]
    emojis = ["📥", "🔍", "📝", "🛠️", "⚙️", "📱", "🚀", "📋"]
    
    # Orbit coordinates: cx=130, cy=100, radius=82
    positions = [
        (114, 2, 130, 18),     # Ingest
        (172, 26, 188, 42),     # Analyze
        (196, 84, 212, 100),    # Brief
        (172, 142, 188, 158),   # Fix
        (114, 166, 130, 182),   # Compile
        (56, 142, 72, 158),     # QA
        (32, 84, 48, 100),      # Release
        (56, 26, 72, 42)        # Report
    ]
    
    # SVG lines setup
    svg_lines = ""
    active_idx = -1
    for idx, status in enumerate(task_statuses):
        if status == "Running":
            active_idx = idx
            
    if active_idx != -1:
        tx, ty = positions[active_idx][2], positions[active_idx][3]
        svg_lines = f"<line x1='130' y1='100' x2='{tx}' y2='{ty}' stroke='#8B5CF6' stroke-width='2' stroke-dasharray='3 3' style='animation: dash 1s linear infinite;' />"

    orbit_html = f"""
    <div style='position: relative; width: 260px; height: 200px; margin: 0 auto;'>
        <svg style='position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1;'>
            <circle cx='130' cy='100' r='82' fill='none' stroke='#334155' stroke-width='1.5' stroke-dasharray='4 4' />
            {svg_lines}
        </svg>
        <div style='width: 48px; height: 48px; position: absolute; top: 76px; left: 106px; border-radius: 50%; background: radial-gradient(circle, #3B82F6 0%, #1E40AF 100%); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 0 20px rgba(59, 130, 246, 0.6); z-index: 10; animation: pulse-glow 2s infinite;'>
            🤖
        </div>
    """
    
    for idx, (label, emoji, status) in enumerate(zip(labels, emojis, task_statuses)):
        left, top, _, _ = positions[idx]
        if status == "Completed":
            border = "2px solid #10B981"
            bg = "rgba(16, 185, 129, 0.15)"
            color = "#10B981"
            anim = ""
        elif status == "Running":
            border = "2px solid #8B5CF6"
            bg = "rgba(139, 92, 246, 0.2)"
            color = "#A78BFA"
            anim = "animation: pulse-glow 1.5s infinite;"
        else:
            border = "1.5px solid #4B5563"
            bg = "#1E293B"
            color = "#9CA3AF"
            anim = ""
            
        orbit_html += f"""
        <div style='width: 32px; height: 32px; position: absolute; top: {top}px; left: {left}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: {bg}; border: {border}; color: {color}; z-index: 5; {anim}' title='{label}'>
            {emoji}
        </div>
        """
    orbit_html += "</div>"
    
    # Generate Grid Cards
    cards_html = "<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 15px; width: 100%;'>"
    for idx, (label, emoji, status) in enumerate(zip(labels, emojis, task_statuses)):
        if status == "Completed":
            badge_color = "#10B981"
            badge_bg = "rgba(16, 185, 129, 0.1)"
            status_text = "Done"
            border_left = "3px solid #10B981"
        elif status == "Running":
            badge_color = "#8B5CF6"
            badge_bg = "rgba(139, 92, 246, 0.15)"
            status_text = "Active"
            border_left = "3px solid #8B5CF6"
        else:
            badge_color = "#6B7280"
            badge_bg = "rgba(107, 114, 128, 0.05)"
            status_text = "Pending"
            border_left = "3px solid #374151"
            
        cards_html += f"""
        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: {border_left}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
            <div style='display: flex; align-items: center;'>
                <span style='margin-right: 6px; font-size: 13px;'>{emoji}</span>
                <span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>{label}</span>
            </div>
            <span style='font-size: 9px; font-weight: bold; background-color: {badge_bg}; color: {badge_color}; padding: 1px 5px; border-radius: 4px;'>{status_text}</span>
        </div>
        """
    cards_html += "</div>"
    
    html_tasks = f"""
    <div style='display: flex; flex-direction: column; align-items: center; width: 100%;'>
        {orbit_html}
        {cards_html}
    </div>
    """
    
    # Generate HTML progress bar
    html_progress = f"""
    <div style='margin-top: 5px; margin-bottom: 15px;'>
        <div style='display: flex; justify-content: space-between; font-size: 11px; color: #9CA3AF; margin-bottom: 2px;'>
            <span>Overall Progress</span>
            <span>{progress_percentage}%</span>
        </div>
        <div style='width: 100%; background-color: #334155; height: 5px; border-radius: 3px; overflow: hidden;'>
            <div style='width: {progress_percentage}%; background-color: #3B82F6; height: 100%; transition: width 0.5s ease-in-out;'></div>
        </div>
    </div>
    """
    
    # Generate HTML Active Agent card
    html_agent = f"""
    <div style='background-color: #1E293B; border-radius: 8px; padding: 10px 12px; border-left: 4px solid #8B5CF6; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; margin-top: 5px; margin-bottom: 10px;'>
        <div style='font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: #9CA3AF; margin-bottom: 2px;'>Current Executor</div>
        <div style='font-size: 14px; font-weight: bold; color: #FFFFFF; display: flex; align-items: center;'>
            <span style='margin-right: 6px;'>👤</span> {current_agent}
        </div>
        <div style='font-size: 11px; color: #60A5FA; margin-top: 3px; line-height: 1.3;'>{current_agent_goal}</div>
    </div>
    """
    
    return html_tasks, html_progress, html_agent

def run_assistant(project_path, github_link, jira_link, raw_text):
    project_path = (project_path or "").strip()
    github_link = (github_link or "").strip()
    jira_link = (jira_link or "").strip()
    raw_text = (raw_text or "").strip()

    if not project_path:
        yield gr.update(), gr.update(), gr.update(), "Error: Android Project Path cannot be empty.", gr.update()
        return

    if github_link:
        source_type = "github_issue"
        source_value = github_link
    elif jira_link:
        source_type = "jira"
        source_value = jira_link
    elif raw_text:
        source_type = "raw_text"
        source_value = raw_text
    else:
        yield gr.update(), gr.update(), gr.update(), "Error: Please provide input in one of the three tabs.", gr.update()
        return

    cmd = [sys.executable, "run.py", source_type, source_value, project_path]
    
    initial_log = f"🚀 Launching Android Engineering Assistant Crew...\n" \
                  f"Source Type: {source_type}\n" \
                  f"Source Value: {source_value}\n" \
                  f"Project Path: {project_path}\n" \
                  f"Command: {' '.join(cmd)}\n" \
                  f"--------------------------------------------------\n\n"
                  
    tasks_html, progress_html, agent_html = parse_subprocess_log("")
    yield tasks_html, progress_html, agent_html, initial_log, gr.update(visible=False)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )

        full_output = initial_log
        for line in iter(process.stdout.readline, ""):
            full_output += line
            tasks_html, progress_html, agent_html = parse_subprocess_log(full_output)
            yield tasks_html, progress_html, agent_html, full_output, gr.update(visible=False)

        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            full_output += f"\n--------------------------------------------------\n" \
                           f"✅ SUCCESS: Crew execution completed successfully!\n"
            
            report_path = os.path.join("output", "pr_report.md")
            report_md = ""
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_md = f.read()
            else:
                report_md = "### ✅ Execution Completed\nFinal report summary was generated inside `output/` directory."
                
            tasks_html, progress_html, agent_html = parse_subprocess_log(full_output + "\nName: final_report_task completed")
            yield tasks_html, progress_html, agent_html, full_output, gr.update(value=report_md, visible=True)
        else:
            full_output += f"\n--------------------------------------------------\n" \
                           f"❌ FAILED: Crew execution failed with exit code {return_code}.\n"
            yield tasks_html, progress_html, agent_html, full_output, gr.update(visible=False)

    except Exception as e:
        yield gr.update(), gr.update(), gr.update(), f"Error executing pipeline: {str(e)}", gr.update(visible=False)

# Custom CSS for setting fixed heights and enforcing single-screen layouts
custom_css = """
@keyframes pulse-glow {
    0% { transform: scale(1); box-shadow: 0 0 2px #3B82F6; }
    50% { transform: scale(1.06); box-shadow: 0 0 18px #3B82F6; }
    100% { transform: scale(1); box-shadow: 0 0 2px #3B82F6; }
}
@keyframes dash {
    to {
        stroke-dashoffset: -20;
    }
}
.gradio-container {
    background-color: #0B0F19 !important;
    color: #E2E8F0 !important;
}
.control-panel {
    background-color: #111827 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 12px !important;
    padding: 15px !important;
    min-height: 640px !important;
    max-height: 640px !important;
    overflow-y: auto !important;
}
.dashboard-panel {
    background-color: #111827 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 12px !important;
    padding: 15px !important;
    min-height: 640px !important;
    max-height: 640px !important;
    overflow-y: auto !important;
}
.log-panel {
    background-color: #111827 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 12px !important;
    padding: 15px !important;
    min-height: 640px !important;
    max-height: 640px !important;
    position: relative !important;
}
.terminal-textarea textarea {
    font-family: 'Fira Code', 'Courier New', monospace !important;
    background-color: #030712 !important;
    color: #34D399 !important;
    border: 1px solid #1F2937 !important;
    font-size: 11px !important;
    line-height: 1.4 !important;
    height: 540px !important;
    max-height: 540px !important;
    overflow-y: auto !important;
}
.report-markdown {
    height: 540px !important;
    max-height: 540px !important;
    overflow-y: auto !important;
    padding: 10px !important;
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
"""

head_html = """
<script>
    console.log("Terminal Auto-Scroll Utility Mounted via HTML Head.");
    
    // Listen to scroll events on any textarea inside .terminal-textarea
    document.addEventListener("scroll", function(e) {
        if (e.target.tagName === "TEXTAREA" && (e.target.classList.contains("terminal-textarea") || e.target.closest(".terminal-textarea"))) {
            var el = e.target;
            // If user is within 40px of bottom, keep autoscroll enabled
            var isAtBottom = (el.scrollHeight - el.scrollTop - el.clientHeight) < 40;
            el.dataset.autoscroll = isAtBottom ? "true" : "false";
        }
    }, { capture: true, passive: true });

    setInterval(function() {
        var textareas = document.querySelectorAll(".terminal-textarea textarea");
        textareas.forEach(function(el) {
            // Default to true if not explicitly set to false by user scrolling up
            if (el.dataset.autoscroll !== "false") {
                el.scrollTop = el.scrollHeight;
            }
        });
    }, 300);
</script>
"""

with gr.Blocks(title="Android Engineering Assistant Dashboard") as demo:
    gr.Markdown(
        """
        # 🤖 Android Engineering Assistant Portal
        *An end-to-end autonomous agent workflow for repository investigation, planning, code modification, build checks, and release management.*
        """
    )

    with gr.Row():
        # Column 1: Control Panel (30% scale width)
        with gr.Column(scale=3, elem_classes=["control-panel"]):
            gr.Markdown("### ⚙️ Target Settings")
            project_path_input = gr.Textbox(
                label="Android Project Path",
                value="/Users/retailopakistan/Documents/tp-app",
                placeholder="Absolute path to target Android project root...",
                lines=1
            )

            gr.Markdown("### 📥 Input Source")
            with gr.Tabs():
                with gr.Tab("Manual Input"):
                    raw_input = gr.Textbox(
                        label="Raw Crash Log / Task Description",
                        placeholder="Paste stack traces or type manually...",
                        lines=5
                    )
                with gr.Tab("GitHub Board"):
                    github_input = gr.Textbox(
                        label="GitHub Issue / PR Link",
                        placeholder="e.g., https://github.com/owner/repo/issues/123",
                        lines=2
                    )
                with gr.Tab("Jira Ticket"):
                    jira_input = gr.Textbox(
                        label="Jira Ticket Link",
                        placeholder="e.g., https://your-domain.atlassian.net/browse/PROJ-123",
                        lines=2
                    )

            submit_btn = gr.Button("🚀 Run Assistant", variant="primary")
            clear_btn = gr.Button("🧹 Clear Inputs")
            
        # Column 2: Dashboard Panel (30% scale width)
        with gr.Column(scale=3, elem_classes=["dashboard-panel"]):
            gr.Markdown("### 📊 Workflow Execution Dashboard")
            progress_bar_html = gr.HTML(
                value="""
                <div style='display: flex; justify-content: space-between; font-size: 11px; color: #9CA3AF;'>
                    <span>Overall Progress</span>
                    <span>0%</span>
                </div>
                <div style='width: 100%; background-color: #334155; height: 5px; border-radius: 3px; overflow: hidden; margin-top: 2px;'>
                    <div style='width: 0%; background-color: #3B82F6; height: 100%;'></div>
                </div>
                """
            )
            
            task_list_html = gr.HTML(
                value="""
                <div style='display: flex; flex-direction: column; align-items: center; width: 100%;'>
                    <div style='position: relative; width: 260px; height: 200px; margin: 0 auto;'>
                        <svg style='position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1;'>
                            <circle cx='130' cy='100' r='82' fill='none' stroke='#334155' stroke-width='1.5' stroke-dasharray='4 4' />
                        </svg>
                        <div style='width: 48px; height: 48px; position: absolute; top: 76px; left: 106px; border-radius: 50%; background: radial-gradient(circle, #3B82F6 0%, #1E40AF 100%); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 0 20px rgba(59, 130, 246, 0.6); z-index: 10;'>
                            🤖
                        </div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 2px; left: 114px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Ingest'>📥</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 26px; left: 172px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Analyze'>🔍</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 84px; left: 196px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Brief'>📝</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 142px; left: 172px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Fix'>🛠️</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 166px; left: 114px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Compile'>⚙️</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 142px; left: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='QA'>📱</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 84px; left: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Release'>🚀</div>
                        <div style='width: 32px; height: 32px; position: absolute; top: 26px; left: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Report'>📋</div>
                    </div>
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 15px; width: 100%;'>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📥</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Ingest</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>🔍</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Analyze</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📝</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Brief</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>🛠️</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Fix</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>⚙️</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Compile</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📱</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>QA</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>🚀</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Release</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                        <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📋</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Report</span></div>
                            <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                        </div>
                    </div>
                </div>
                """
            )

            active_agent_html = gr.HTML(
                value="""
                <div style='background-color: #1E293B; border-radius: 8px; padding: 10px 12px; border-left: 4px solid #3B82F6; border: 1px solid #334155;'>
                    <div style='font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: #9CA3AF; margin-bottom: 2px;'>Current Executor</div>
                    <div style='font-size: 14px; font-weight: bold; color: #FFFFFF;'>System Router</div>
                    <div style='font-size: 11px; color: #9CA3AF; margin-top: 3px;'>Awaiting kickoff...</div>
                </div>
                """
            )

        # Column 3: Live Output Terminal & Compiled Report (4% scale width)
        with gr.Column(scale=4, elem_classes=["log-panel"]):
            with gr.Tabs() as right_tabs:
                with gr.Tab("🖥️ Real-time Execution Stream"):
                    gr.HTML(
                        """
                        <div style='position: absolute; top: 12px; right: 15px; z-index: 1000;'>
                            <button onclick="var t=document.querySelector('.terminal-textarea textarea'); if(t) { navigator.clipboard.writeText(t.value); var b=document.getElementById('copy-btn'); b.innerText='✅ Copied!'; setTimeout(function(){b.innerText='📋 Copy Logs';}, 1500); }" id="copy-btn" style="background-color: #3B82F6; color: white; border: none; padding: 5px 12px; border-radius: 6px; font-size: 11px; cursor: pointer; font-weight: bold; transition: background-color 0.2s; box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);">📋 Copy Logs</button>
                        </div>
                        """
                    )
                    logs_output = gr.Textbox(
                        label="Log Stream Output",
                        placeholder="Live logs will stream here line-by-line...",
                        lines=22,
                        interactive=False,
                        autoscroll=True,
                        elem_classes=["terminal-textarea"]
                    )
                with gr.Tab("📄 Compiled Engineering PR Report"):
                    final_report_md = gr.Markdown(
                        value="*Report summary will be displayed here once execution completes.*",
                        visible=True,
                        elem_classes=["report-markdown"]
                    )

    # Click triggers
    submit_btn.click(
        fn=run_assistant,
        inputs=[project_path_input, github_input, jira_input, raw_input],
        outputs=[task_list_html, progress_bar_html, active_agent_html, logs_output, final_report_md]
    )

    def reset_inputs():
        default_tasks = """
        <div style='display: flex; flex-direction: column; align-items: center; width: 100%;'>
            <div style='position: relative; width: 260px; height: 200px; margin: 0 auto;'>
                <svg style='position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1;'>
                    <circle cx='130' cy='100' r='82' fill='none' stroke='#334155' stroke-width='1.5' stroke-dasharray='4 4' />
                </svg>
                <div style='width: 48px; height: 48px; position: absolute; top: 76px; left: 106px; border-radius: 50%; background: radial-gradient(circle, #3B82F6 0%, #1E40AF 100%); display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 0 20px rgba(59, 130, 246, 0.6); z-index: 10;'>
                    🤖
                </div>
                <div style='width: 32px; height: 32px; position: absolute; top: 2px; left: 114px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Ingest'>📥</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 26px; left: 172px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Analyze'>🔍</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 84px; left: 196px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Brief'>📝</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 142px; left: 172px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Fix'>🛠️</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 166px; left: 114px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Compile'>⚙️</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 142px; left: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='QA'>📱</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 84px; left: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Release'>🚀</div>
                <div style='width: 32px; height: 32px; position: absolute; top: 26px; left: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; background-color: #1E293B; border: 1.5px solid #4B5563; color: #9CA3AF;' title='Report'>📋</div>
            </div>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 15px; width: 100%;'>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📥</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Ingest</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>🔍</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Analyze</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📝</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Brief</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>🛠️</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Fix</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>⚙️</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Compile</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📱</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>QA</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>🚀</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Release</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
                <div style='background-color: #1E293B; border-radius: 6px; padding: 6px 10px; border-left: 3px solid #374151; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center;'><span style='margin-right: 6px; font-size: 13px;'>📋</span><span style='font-size: 11px; font-weight: bold; color: #E2E8F0;'>Report</span></div>
                    <span style='font-size: 9px; font-weight: bold; background-color: rgba(107,114,128,0.05); color: #6B7280; padding: 1px 5px; border-radius: 4px;'>Pending</span>
                </div>
            </div>
        </div>
        """
        default_progress = """
        <div style='display: flex; justify-content: space-between; font-size: 11px; color: #9CA3AF;'>
            <span>Overall Progress</span>
            <span>0%</span>
        </div>
        <div style='width: 100%; background-color: #334155; height: 5px; border-radius: 3px; overflow: hidden; margin-top: 2px;'>
            <div style='width: 0%; background-color: #3B82F6; height: 100%;'></div>
        </div>
        """
        default_agent = """
        <div style='background-color: #1E293B; border-radius: 8px; padding: 10px 12px; border-left: 4px solid #3B82F6; border: 1px solid #334155;'>
            <div style='font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: #9CA3AF; margin-bottom: 2px;'>Current Executor</div>
            <div style='font-size: 14px; font-weight: bold; color: #FFFFFF;'>System Router</div>
            <div style='font-size: 11px; color: #9CA3AF; margin-top: 3px;'>Awaiting kickoff...</div>
        </div>
        """
        return "/Users/retailopakistan/Documents/tp-app", "", "", "", default_tasks, default_progress, default_agent, "Logs cleared. Ready.", "*Report summary will be displayed here once execution completes.*"

    clear_btn.click(
        fn=reset_inputs,
        inputs=[],
        outputs=[project_path_input, github_input, jira_input, raw_input, task_list_html, progress_bar_html, active_agent_html, logs_output, final_report_md]
    )

    # Script loaded via HTML head instead to prevent Gradio innerHTML warnings

if __name__ == "__main__":
    demo.queue()
    # Share = False inside sandbox
    demo.launch(server_name="0.0.0.0", share=False, css=custom_css, head=head_html)
