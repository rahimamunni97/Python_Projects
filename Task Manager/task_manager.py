#!/usr/bin/env python3
"""
Simple Task Manager - A command-line task management application
"""

import json
import os
from datetime import datetime

TASKS_FILE = "tasks.json"

def load_tasks():
    """Load tasks from JSON file"""
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_tasks(tasks):
    """Save tasks to JSON file"""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

def add_task(tasks):
    """Add a new task"""
    title = input("Enter task title: ").strip()
    if not title:
        print("Task title cannot be empty!")
        return
    
    description = input("Enter task description (optional): ").strip()
    
    task = {
        "id": len(tasks) + 1,
        "title": title,
        "description": description,
        "completed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    tasks.append(task)
    save_tasks(tasks)
    print(f"✓ Task '{title}' added successfully!")

def list_tasks(tasks):
    """Display all tasks"""
    if not tasks:
        print("No tasks found. Add a task to get started!")
        return
    
    print("\n" + "="*50)
    print("YOUR TASKS")
    print("="*50)
    
    for task in tasks:
        status = "✓" if task["completed"] else "○"
        print(f"\n[{status}] Task #{task['id']}: {task['title']}")
        if task['description']:
            print(f"   Description: {task['description']}")
        print(f"   Created: {task['created_at']}")
    
    print("\n" + "="*50)

def complete_task(tasks):
    """Mark a task as completed"""
    if not tasks:
        print("No tasks to complete!")
        return
    
    list_tasks(tasks)
    try:
        task_id = int(input("\nEnter task ID to mark as complete: "))
        task = next((t for t in tasks if t["id"] == task_id), None)
        
        if task:
            if task["completed"]:
                print("Task is already completed!")
            else:
                task["completed"] = True
                save_tasks(tasks)
                print(f"✓ Task '{task['title']}' marked as complete!")
        else:
            print("Task not found!")
    except ValueError:
        print("Please enter a valid task ID!")

def delete_task(tasks):
    """Delete a task"""
    if not tasks:
        print("No tasks to delete!")
        return
    
    list_tasks(tasks)
    try:
        task_id = int(input("\nEnter task ID to delete: "))
        task = next((t for t in tasks if t["id"] == task_id), None)
        
        if task:
            tasks.remove(task)
            # Reassign IDs
            for i, t in enumerate(tasks, 1):
                t["id"] = i
            save_tasks(tasks)
            print(f"✓ Task '{task['title']}' deleted successfully!")
        else:
            print("Task not found!")
    except ValueError:
        print("Please enter a valid task ID!")

def show_stats(tasks):
    """Show task statistics"""
    total = len(tasks)
    completed = sum(1 for t in tasks if t["completed"])
    pending = total - completed
    
    print("\n" + "="*50)
    print("TASK STATISTICS")
    print("="*50)
    print(f"Total tasks: {total}")
    print(f"Completed: {completed}")
    print(f"Pending: {pending}")
    if total > 0:
        percentage = (completed / total) * 100
        print(f"Completion rate: {percentage:.1f}%")
    print("="*50 + "\n")

def main():
    """Main function to run the task manager"""
    print("="*50)
    print("Welcome to Task Manager!")
    print("="*50)
    
    tasks = load_tasks()
    
    while True:
        print("\nOptions:")
        print("1. Add Task")
        print("2. List Tasks")
        print("3. Complete Task")
        print("4. Delete Task")
        print("5. Show Statistics")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            add_task(tasks)
        elif choice == "2":
            list_tasks(tasks)
        elif choice == "3":
            complete_task(tasks)
        elif choice == "4":
            delete_task(tasks)
        elif choice == "5":
            show_stats(tasks)
        elif choice == "6":
            print("Thank you for using Task Manager! Goodbye!")
            break
        else:
            print("Invalid choice! Please enter a number between 1-6.")

if __name__ == "__main__":
    main()

