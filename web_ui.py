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
    started = re.findall(r"(?:Task Started|Name:\s*)(\w+_task)", full_log)
    for t_name in started:
        if t_name in task_mapping:
            idx = task_mapping[t_name]
            task_statuses[idx] = "Running"
            # Set preceding tasks as completed
            for i in range(idx):
                if task_statuses[i] in ("Pending", "Running"):
                    task_statuses[i] = "Completed"
                    
    # Find completed tasks
    completed = re.findall(r"(?:Task Completed|Name:\s*)(\w+_task)", full_log)
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
    
    # Generate HTML task list as horizontal circles
    labels = ["Ingest", "Analyze", "Brief", "Fix", "Compile", "QA", "Release", "Report"]
    emojis = ["📥", "🔍", "📝", "🛠️", "⚙️", "📱", "🚀", "📋"]
    
    html_tasks = "<div style='display: flex; align-items: center; justify-content: space-between; width: 100%; margin-top: 15px; margin-bottom: 15px; padding: 10px 0; overflow-x: auto; scrollbar-width: none;'>"
    
    for idx, (label, emoji, status) in enumerate(zip(labels, emojis, task_statuses)):
        if status == "Completed":
            color = "#10B981"  # Emerald Green
            bg = "rgba(16, 185, 129, 0.15)"
            border = "2px solid #10B981"
            text_color = "#10B981"
            anim = ""
        elif status == "Running":
            color = "#8B5CF6"  # Purple
            bg = "rgba(139, 92, 246, 0.2)"
            border = "2px solid #8B5CF6"
            text_color = "#A78BFA"
            anim = "animation: pulse-glow 1.5s infinite;"
        else:
            color = "#4B5563"  # Gray
            bg = "#1E293B"
            border = "2px solid #4B5563"
            text_color = "#9CA3AF"
            anim = ""
            
        # Draw node
        html_tasks += f"""
        <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
            <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: {bg}; border: {border}; color: {text_color}; {anim}'>
                {emoji}
            </div>
            <span style='font-size: 10px; font-weight: bold; color: {text_color}; margin-top: 6px; white-space: nowrap;'>{label}</span>
        </div>
        """
        
        # Draw connector line if not the last node
        if idx < len(labels) - 1:
            next_status = task_statuses[idx + 1]
            if status == "Completed" and next_status in ("Completed", "Running"):
                line_color = "#10B981"
                line_style = "solid"
            elif status == "Completed" or next_status == "Running":
                line_color = "#8B5CF6"
                line_style = "dashed"
            else:
                line_color = "#374151"
                line_style = "dotted"
                
            html_tasks += f"<div style='flex-grow: 1; height: 0; border-top: 2px {line_style} {line_color}; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>"
            
    html_tasks += "</div>"
    
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
    0% { transform: scale(1); box-shadow: 0 0 2px #8B5CF6; }
    50% { transform: scale(1.08); box-shadow: 0 0 12px #8B5CF6; }
    100% { transform: scale(1); box-shadow: 0 0 2px #8B5CF6; }
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
}
.terminal-textarea textarea {
    font-family: 'Fira Code', 'Courier New', monospace !important;
    background-color: #030712 !important;
    color: #34D399 !important;
    border: 1px solid #1F2937 !important;
    font-size: 11px !important;
    line-height: 1.4 !important;
    height: 520px !important;
    max-height: 520px !important;
    overflow-y: auto !important;
}
.report-markdown {
    height: 520px !important;
    max-height: 520px !important;
    overflow-y: auto !important;
    padding: 10px !important;
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
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
            
        # Column 2: Dashboard Panel (3% scale width)
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
                <div style='display: flex; align-items: center; justify-content: space-between; width: 100%; margin-top: 15px; margin-bottom: 15px; padding: 10px 0; overflow-x: auto; scrollbar-width: none;'>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📥</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Ingest</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>🔍</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Analyze</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📝</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Brief</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>🛠️</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Fix</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>⚙️</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Compile</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📱</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>QA</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>🚀</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Release</span>
                    </div>
                    <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
                    <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                        <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📋</div>
                        <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Report</span>
                    </div>
                </div>
                """
            )

            active_agent_html = gr.HTML(
                value="""
                <div style='background-color: #1E293B; border-radius: 8px; padding: 10px 12px; border-left: 4px solid #8B5CF6; border: 1px solid #334155;'>
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
        <div style='display: flex; align-items: center; justify-content: space-between; width: 100%; margin-top: 15px; margin-bottom: 15px; padding: 10px 0; overflow-x: auto; scrollbar-width: none;'>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📥</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Ingest</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>🔍</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Analyze</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📝</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Brief</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>🛠️</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Fix</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>⚙️</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Compile</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📱</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>QA</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>🚀</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Release</span>
            </div>
            <div style='flex-grow: 1; height: 0; border-top: 2px dotted #374151; margin: 0 2px; min-width: 6px; margin-top: -16px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center; min-width: 52px; text-align: center;'>
                <div style='width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; background-color: #1E293B; border: 2px solid #4B5563; color: #9CA3AF;'>📋</div>
                <span style='font-size: 10px; font-weight: bold; color: #9CA3AF; margin-top: 6px;'>Report</span>
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

if __name__ == "__main__":
    demo.queue()
    # Share = False inside sandbox
    demo.launch(server_name="0.0.0.0", share=False, css=custom_css)
