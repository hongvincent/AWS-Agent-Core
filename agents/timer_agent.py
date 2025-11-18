"""
Timer Agent for AWS Bedrock AgentCore Long-Running Session Testing

This agent tests:
- Long-running session support (up to 8 hours as per AgentCore specs)
- Periodic logging
- Session state maintenance
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/timer_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class TimerAgent:
    """Agent for testing long-running sessions"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or self._generate_session_id()
        self.start_time = datetime.now()
        self.timestamps: List[str] = []
        logger.info(f"TimerAgent initialized at {self.start_time.isoformat()}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"timer_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def run_timed_loop(self, duration_minutes: int = 5, interval_minutes: int = 1) -> Dict[str, Any]:
        """
        Run a timed loop that logs timestamps at regular intervals

        Args:
            duration_minutes: Total duration to run (default 5 minutes)
            interval_minutes: Interval between logs (default 1 minute)

        Returns:
            Dict containing execution results and timestamps
        """
        logger.info(f"Starting timed loop: {duration_minutes}min total, {interval_minutes}min interval")

        duration_seconds = duration_minutes * 60
        interval_seconds = interval_minutes * 60
        end_time = time.time() + duration_seconds

        iteration = 0
        while time.time() < end_time:
            iteration += 1
            current_time = datetime.now().isoformat()
            elapsed = (datetime.now() - self.start_time).total_seconds()

            self.timestamps.append(current_time)
            logger.info(f"[Iteration {iteration}] Timestamp: {current_time} | Elapsed: {elapsed:.1f}s")

            # Write to file for persistence testing
            self._write_checkpoint(iteration, current_time, elapsed)

            # Sleep until next interval (or end)
            remaining = end_time - time.time()
            sleep_duration = min(interval_seconds, remaining)

            if sleep_duration > 0:
                logger.info(f"Sleeping for {sleep_duration:.1f}s...")
                time.sleep(sleep_duration)

        total_elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"Timed loop completed. Total elapsed: {total_elapsed:.1f}s")

        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_elapsed_seconds": total_elapsed,
            "iterations": iteration,
            "timestamps": self.timestamps,
            "status": "completed"
        }

    def _write_checkpoint(self, iteration: int, timestamp: str, elapsed: float) -> None:
        """Write checkpoint data to file"""
        checkpoint_file = "/tmp/timer_checkpoints.log"
        with open(checkpoint_file, 'a') as f:
            f.write(f"{iteration},{timestamp},{elapsed:.2f}\n")

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            "timestamps_collected": len(self.timestamps),
            "status": "running"
        }


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Lambda/AgentCore Runtime handler function

    Args:
        event: Input event with configuration
        context: Lambda context (optional)

    Returns:
        Response dict with execution results
    """
    try:
        # Extract parameters
        session_id = event.get('session_id')
        action = event.get('action', 'run')
        duration_minutes = event.get('duration_minutes', 5)
        interval_minutes = event.get('interval_minutes', 1)

        # Initialize agent
        agent = TimerAgent(session_id=session_id)

        if action == 'run':
            result = agent.run_timed_loop(duration_minutes, interval_minutes)
        elif action == 'status':
            result = agent.get_status()
        else:
            result = {"error": f"Unknown action: {action}"}

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except Exception as e:
        logger.error(f"Error in timer agent: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }


if __name__ == "__main__":
    # Test locally with shorter duration
    print("Testing TimerAgent with 2-minute duration, 30-second intervals...")

    event = {
        "action": "run",
        "duration_minutes": 2,
        "interval_minutes": 0.5  # 30 seconds
    }

    result = handler(event)
    print(f"\n{'='*60}")
    print("Result:")
    print(json.dumps(json.loads(result['body']), indent=2))
