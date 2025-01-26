import json
import os

class PrintTask:
  def __init__(self):
      self.model_name = None
      self.task_id = None
      self.ams_mapping = None
      self.total_weight = 0
      self.start_time = None
      self.end_time = None
      self.filament_used = None
      self.init_percent = 0
      self.percent_complete = 0
      self.status = None

  def to_dict(self):
      """Convert the PrintTask object to a dictionary."""
      return {
          "model_name": self.model_name,
          "task_id": self.task_id,
          "ams_mapping": self.ams_mapping,
          "total_weight": self.total_weight,
          "start_time": self.start_time,
          "end_time": self.end_time,
          "filament_used": self.filament_used,
          "init_percent": self.init_percent,
          "percent_complete": self.percent_complete,
          "status": self.status,
      }
      
  def CleanTask(self):
      """Clean the task object."""
      self.model_name = None
      self.task_id = None
      self.ams_mapping = None
      self.total_weight = 0
      self.start_time = None
      self.end_time = None
      self.filament_used = None
      self.init_percent = 0
      self.percent_complete = 0
      self.status = None
      
  def SaveTask(self):
      """Save the task to a task.txt file as a JSON object."""
      file_name = "task.txt"
      
      # Load existing tasks if the file exists
      if os.path.exists(file_name):
          with open(file_name, "r") as file:
              try:
                  tasks = json.load(file)
              except json.JSONDecodeError:
                  # If the file is corrupted or empty, start with an empty list
                  tasks = []
      else:
          tasks = []
      
      # Append the current task
      tasks.append(self.to_dict())
      
      # Save back to the file
      with open(file_name, "w") as file:
          json.dump(tasks, file, indent=4)
      
      print(f"Task saved successfully to {file_name}.")