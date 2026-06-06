"""
ME4 TestSimulator — SMproducer Autorun Workflows
Pre-defined workflows for automated SMproducer testing.
"""

from .webdriver import WebDriver

class SMproducerAutorun:
    """Automated SMproducer workflow runner."""
    
    def __init__(self, url: str = "http://localhost:5173", headless: bool = False):
        self.url = url
        self.driver = WebDriver(headless=headless)
        self.state = "idle"  # idle, running, waiting, done, error
    
    def start(self):
        """Start the autorun workflow."""
        self.state = "running"
        self.driver.start(self.url)
        return self
    
    def step_select_channel(self, channel_prefix: str = "technews"):
        """Step 1: Select a channel."""
        self.driver.sleep(1)
        # Click channel selector
        try:
            self.driver.click_text(channel_prefix)
        except:
            # Fallback: click the channel dropdown
            self.driver.click("[data-testid='channel-selector']")
            self.driver.sleep(0.5)
            self.driver.click_text(channel_prefix)
        self.driver.sleep(0.5)
        return self
    
    def step_new_project(self):
        """Step 2: Start a new project."""
        self.driver.click_text("+ Neues Projekt")
        self.driver.sleep(0.5)
        return self
    
    def step_add_youtube_source(self, youtube_url: str):
        """Step 3: Add YouTube URL as source."""
        self.driver.click_text("YouTube (URL)")
        self.driver.sleep(0.3)
        # Type YouTube URL
        self.driver.type_into("https://www.youtube.com/watch?v=", youtube_url)
        self.driver.sleep(0.3)
        self.driver.click_text("Hinzufügen")
        self.driver.sleep(2)  # Wait for YouTube data to load
        return self
    
    def step_send_to_ai(self):
        """Step 4: Send to AI for analysis."""
        self.driver.click_text("An KI senden")
        self.driver.sleep(3)  # Wait for AI processing
        return self
    
    def step_wait_for_decision(self):
        """Pause at decision point — wait for user input."""
        self.state = "waiting"
        return self
    
    def step_continue_after_decision(self):
        """Continue after user made topic selection."""
        self.state = "running"
        return self
    
    def stop(self):
        """Stop and cleanup."""
        self.state = "done"
        self.driver.stop()
        return self


def run_youtube_workflow(youtube_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                         channel: str = "technews",
                         headless: bool = False):
    """
    Full workflow: YouTube → Topic → Decision Point.
    Returns the autorun instance so caller can resume after decision.
    """
    ar = SMproducerAutorun(headless=headless)
    ar.start()
    ar.step_select_channel(channel)
    ar.step_new_project()
    ar.step_add_youtube_source(youtube_url)
    ar.step_send_to_ai()
    ar.step_wait_for_decision()
    return ar  # Caller resumes with: ar.step_continue_after_decision()
