import json
import os
import Spoolman.spoolman_filament as spoolman_filament

class PrintTask:
  def __init__(self):
      self.model_name = None
      self.task_id = None
      self.job_id = None
      self.ams_mapping = None
      self.total_weight = 0
      self.start_time = None
      self.end_time = None
      self.teoric_filaments = None
      self.reported_filament = None
      self.init_percent = 0
      self.percent_complete = 0
      self.status = None
      self.image_cover_url = None

  def to_dict(self):
      """Convert the PrintTask object to a dictionary."""
      return {
          "model_name": self.model_name,
          "task_id": self.task_id,
          "job_id": self.job_id,
          "total_weight": self.total_weight,
          "start_time": self.start_time,
          "end_time": self.end_time,
          "teoric_filaments": self.teoric_filaments,
          "reported_filament": self.reported_filament,
          "init_percent": self.init_percent,
          "percent_complete": self.percent_complete,
          "status": self.status,
          "image_cover_url": self.image_cover_url
      }
      
  def CleanTask(self):
      """Clean the task object."""
      self.model_name = None
      self.task_id = None
      self.job_id = None
      self.total_weight = 0
      self.start_time = None
      self.end_time = None
      self.teoric_filaments = None
      self.reported_filament = None
      self.init_percent = 0
      self.percent_complete = 0
      self.status = None
      self.image_cover_url = None
      
  def ReportAndSaveTask(self):
      """Save the task to a task.txt file as a JSON object."""
      file_name = "task.txt"
      if self.percent_complete != 0:
        if self.teoric_filaments:
            self.reported_filament = []  # Inicializar si es None
            if self.percent_complete == 100:
                print("Complete Taks")
                multiplier = 1
            else:
                print("No complete task")
                try:
                    multiplier = (self.percent_complete-self.init_percent)/(100-self.init_percent)
                except:
                    multiplier = 1
                    print("Error calculating multiplier")
                print("Using multiplier: ", multiplier)
                
            for filament in self.teoric_filaments:
                saved_filament = spoolman_filament.RegisterFilament(filament["filamentId"], multiplier*filament["weight"])
                if saved_filament == True:
                    self.reported_filament.append(filament)
      
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