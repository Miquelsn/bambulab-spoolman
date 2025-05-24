import json
import BambuCloud
import BambuCloud.projects
from enum import Enum
from BambuPrinter.print_task import PrintTask
import time
from datetime import datetime
from helper_logs import logger


class State (Enum):
  IDLE = 0
  PREPARING  = 1
  PRINTING = 2
  FAILED = 3
  UNKWON = 4


class BambuPrinter:
  
  def __init__(self):
    self.current_state = State.UNKWON
    self.new_state = State.UNKWON
    self.current_gcode = None 
    self.current_filament = None
    self.current_percent = 0
    self.print_task = PrintTask()
    self.first_time = True
    self.complete_task = False
    self.externalFilamentID = 0

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
    
    
  def AMSFilamentParser(self, msg):
    pass

  def ExternalFilamentParser(self, msg):
    if "tray_info_idx" in msg:
      self.externalFilamentID = msg["tray_info_idx"]
    pass


  def SetWeightDetail(self, task_id):
    self.print_task.task_id = task_id
    if task_id == "0":
      logger.log_error("Task ID is 0. This integration just works with cloud print tasks")
      return
    job_id = BambuCloud.projects.GetJobID(task_id)
    self.print_task.job_id = job_id
    task_detail = BambuCloud.projects.GetTaksDetail(job_id)
    if task_detail is not None:
      self.print_task.total_weight = task_detail["weight"]
      self.print_task.model_name = task_detail["title"]
      self.print_task.image_cover_url = task_detail["cover"]
      
      # ToDo: This is ams filament. If empty get filament from external spool mqtt
      ## object►print►vt_tray►tray_info_idx is the filament ID. Weight can be getted from weight in task detail
      filament = []
      nonAsignedFilament = 0
      for ams in task_detail["amsDetailMapping"]:
        if ams["filamentId"] == "":
          logger.log_info("Filament ID empty. Asigning to external spool")
          nonAsignedFilament += task_detail["weight"]
          
        logger.log_info(ams["filamentId"])
        logger.log_info(ams["weight"])
        filament.append({ "filamentId": ams["filamentId"], "weight": ams["weight"]})
      if nonAsignedFilament > 0:
        logger.log_error("Non asigned filament: ",nonAsignedFilament)
        filament.append({ "filamentId": self.externalFilamentID, "weight": nonAsignedFilament})
      self.print_task.teoric_filaments = filament

  def SetPrintPercentatge(self, percentage):
    self.current_percent = percentage

  def SetCurrentState(self, id):
    logger.log_info(f"Current state {id}")
    if id == 0:
      self.new_state = State.PRINTING
    elif (id == 1 or id == 8 or id == 2) and self.current_state == State.IDLE:
       self.new_state = State.PREPARING
    elif id == 255:
      self.new_state = State.IDLE
    else:
      logger.log_error(f"Undefined state id: {id}")
    self.ComprobateState()
    
    
  def SetGcodeState(self, gcode):
    logger.log_info(f"Gcode state {gcode}")
    if gcode == "FAILED":
      self.new_state = State.FAILED
    elif gcode == "PREPARE":
      self.new_state = State.PREPARING
    elif gcode == "FINISH":
      self.new_state = State.IDLE
    self.ComprobateState()
      
      
  def ComprobateState(self):

    # Correct sync on first time event
    if self.first_time:
      self.first_time = False
      self.complete_task = False
      self.current_state = self.new_state
      self.print_task.CleanTask()
      return
    
    if self.current_state != self.new_state:
      # Finished task printing. Print task is saved.
      if self.new_state == State.IDLE and self.current_state == State.PRINTING:
        logger.log_info("Printer is idle.")
        self.print_task.percent_complete = self.current_percent
        self.print_task.status = "Complete"
        self.print_task.end_time = datetime.now().strftime("%H:%M:%S-%d-%m-%Y")
        logger.log_info("Task complete", self.complete_task)
        if self.complete_task == True:
          self.print_task.ReportAndSaveTask()
        self.complete_task = False
        
      # Print taks is received and start preparing
      elif(self.new_state == State.PREPARING):
        logger.log_info("Printer is preparing.")
        self.complete_task = True
        self.print_task.CleanTask()
        self.print_task.start_time = datetime.now().strftime("%H:%M:%S-%d-%m-%Y")
        
      # Print taks is received and start printing without preparing
      elif(self.new_state == State.PRINTING and self.current_state != State.PREPARING):
        logger.log_info("Printer is printing.")
        self.complete_task = True
        self.print_task.CleanTask()
        self.print_task.start_time = datetime.now().strftime("%H:%M:%S-%d-%m-%Y")
        self.print_task.init_percent = self.current_percent

      # Activate when really stating to print
      elif self.new_state == State.PRINTING:
        self.print_task.init_percent = self.current_percent
        
      # Print task is cancelled or failed. Print task is saved.
      elif self.new_state == State.FAILED and self.current_state == State.PRINTING:
        logger.log_info("Print failed.")
        self.print_task.percent_complete = self.current_percent
        self.print_task.status = "Failed"
        self.print_task.end_time = datetime.now().strftime("%H:%M:%S-%d-%m-%Y")
        if self.complete_task == True:
          self.print_task.ReportAndSaveTask()
        self.complete_task = False
        self.new_state = State.IDLE
        
      logger.log_info(f"State change from {self.current_state.name} to {self.new_state.name}")
      self.current_state = self.new_state


bambu_printer = BambuPrinter()