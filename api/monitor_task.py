#!/usr/bin/env python3
"""
Task progress monitor for SlideSpeaker
Usage: uv run python monitor_task.py <task_id>
"""

import asyncio
import sys
from slidespeaker.core.task_queue import task_queue
from slidespeaker.core.state_manager import state_manager

async def monitor_task(task_id: str) -> None:
    """Monitor the progress of a specific task"""
    
    # Get task details
    task = await task_queue.get_task(task_id)
    if not task:
        print(f"Task {task_id} not found")
        return
    
    print(f"=== Task Progress: {task_id} ===")
    print(f"Status: {task.get('status')}")
    print(f"Type: {task.get('task_type')}")
    
    # Get processing state
    file_id = task.get('kwargs', {}).get('file_id')
    if file_id:
        state = await state_manager.get_state(file_id)
        if state:
            print(f"\nFile ID: {file_id}")
            print(f"Current Step: {state.get('current_step', 'Unknown')}")
            print(f"Overall Status: {state.get('status', 'Unknown')}")
            
            print("\nStep Progress:")
            for step_name, step_data in state.get('steps', {}).items():
                status = step_data.get('status')
                if status == 'completed':
                    print(f"  ✅ {step_name}: {status}")
                elif status == 'processing':
                    print(f"  🔄 {step_name}: {status}")
                elif status == 'failed':
                    print(f"  ❌ {step_name}: {status}")
                elif status == 'pending':
                    print(f"  ⏳ {step_name}: {status}")
                elif status == 'skipped':
                    print(f"  ⏭️  {step_name}: {status}")
                else:
                    print(f"  📝 {step_name}: {status}")
            
            if task.get('error'):
                print(f"\nError: {task.get('error')}")
        else:
            print("No state found for this task")
    else:
        print("No file_id in task kwargs")

async def monitor_latest():
    """Monitor the latest task"""
    keys = await task_queue.redis_client.keys('ai_slider:task:*')
    latest_task = None
    
    for key in keys:
        if not key.endswith(':cancelled'):
            task_data = await task_queue.redis_client.get(key)
            if task_data:
                import json
                task = json.loads(task_data)
                if task.get('task_type') == 'process_presentation':
                    if not latest_task or task.get('updated_at', '') > latest_task.get('updated_at', ''):
                        latest_task = task
    
    if latest_task:
        await monitor_task(latest_task['task_id'])
    else:
        print("No presentation tasks found")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        asyncio.run(monitor_task(task_id))
    else:
        asyncio.run(monitor_latest())