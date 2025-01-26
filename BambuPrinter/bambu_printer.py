import json
import BambuCloud
import BambuCloud.projects
from enum import Enum
from BambuPrinter.print_task import PrintTask
import time

class State (Enum):
  IDLE = 0
  PREPARING  = 1
  PRINTING = 2
  FAILED = 3


class BambuPrinter:
  
  def __init__(self):
    self.current_state = State.IDLE
    self.new_state = State.IDLE
    self.current_gcode = None 
    self.current_filament = None
    self.current_percent = 0
    self.print_task = PrintTask()
    self.first_time = True


  def ProccessMQTTMsg(self, msg):
    data = msg.payload.decode()
    parsed_data = json.loads(data)
    if "print" in parsed_data:
      parsed_data = parsed_data["print"]
      if "mc_percent" in parsed_data:
        self.SetPrintPercentatge(parsed_data["mc_percent"])
      if "stg_cur" in  parsed_data:
        self.SetCurrentState(parsed_data["stg_cur"])
      if "gcode_state" in  parsed_data: 
        self.SetGcodeState(parsed_data["gcode_state"])
      if "task_id" in  parsed_data:
        self.SetWeightDetail(parsed_data["task_id"])
      if "ams" in parsed_data:
        self.AMSFilamentParser(parsed_data["ams"])
      if "vt_tray" in parsed_data:
        self.ExternalFilamentParser(parsed_data["vt_tray"])
    else:
      pass
      #print("No print key in the message")
      #print(parsed_data)
    
    
  def AMSFilamentParser(self, msg):
    #print(msg)
    pass

  def ExternalFilamentParser(self, msg):
    #print(msg)
    pass


  def SetWeightDetail(self, task_id):
    self.print_task.task_id = task_id
    task_detail = BambuCloud.projects.GetTaksDetail(task_id)
    if task_detail is not None:
      print(task_detail)
      self.print_task.total_weight = task_detail["weight"]
      self.print_task.model_name = task_detail["title"]

  def SetPrintPercentatge(self, percentage):
    self.current_percent = percentage

  def SetCurrentState(self, id):
    newState = None
    if id == 0:
      newState = State.PRINTING
    # elif id == 1 or id == 8 or id == 2:
    #   newState = State.PREPARING
    elif id == 255:
      newState = State.IDLE
    else:
      print(f"Undefined state id: {id}")
    self.ComprobateState()
    
    
  def SetGcodeState(self, gcode):
    if gcode == "FAILED":
      self.new_state = State.FAILED
    elif gcode == "PREPARE":
      self.new_state = State.PREPARING
    elif gcode == "RUNNING" and self.current_state != State.PRINTING:
      self.new_state = State.PREPARING
    self.ComprobateState()
      
      
  def ComprobateState(self):
    # Correct sync on first time event
    if self.first_time:
      self.first_time = False
      self.current_state = self.new_state
      self.print_task.CleanTask()
      return
    
    if self.current_state != self.new_state:
      # Finished task printing. Print task is saved.
      if(self.new_state == State.IDLE):
        print("Printer is idle.")
        self.print_task.percent_complete = self.current_percent
        self.print_task.status = "Complete"
        self.print_task.end_time = time.time()
        self.print_task.SaveTask()
        
      # Print taks is received and start preparing
      elif(self.new_state == State.PREPARING):
        print("Printer is preparing.")
        self.print_task.CleanTask()
        self.print_task.start_time = time.time()
        
      # Print taks is received and start printing without preparing
      elif(self.new_state == State.PRINTING and self.current_state != State.PREPARING):
        print("Printer is printing.")
        self.print_task.CleanTask()
        self.print_task.start_time = time.time()
        self.print_task.init_percent = self.current_percent

      # Activate when really stating to print
      elif(self.new_state == State.PRINTING):
        self.print_task.init_percent = self.current_percent
        
      # Print task is cancelled or failed. Print task is saved.
      elif(self.new_state == State.FAILED):
        print("Print failed.")
        self.print_task.percent_complete = self.current_percent
        self.print_task.status = "Failed"
        self.print_task.end_time = time.time()
        self.print_task.SaveTask()
        
      print(f"State change from {self.current_state.name} to {self.new_state.name}")
      self.current_state = self.new_state


bambu_printer = BambuPrinter()