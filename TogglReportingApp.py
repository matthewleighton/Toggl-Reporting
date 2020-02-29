"""
#To Do List:
- Add title to graph, showing timespan.
- Improve the way that project selection is displayed. Maybe list most tracked projects at top?
- Ability to serach by task description (Compare different tasks?)
"""

import time
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkcalendar import Calendar, DateEntry
from toggl.TogglPy import Toggl

from datetime import datetime, timedelta

import csv
import io
import re

import tempfile

import matplotlib.pyplot as plt

import config

import math

LARGE_FONT = ("Verdana", 12)

# TogglReportingApp Class -------------------------------------------------------------------------------------------
class TogglReportingApp(tk.Tk):

	def __init__(self, *args, **kwargs):
		self.connect_to_toggl()
		self.get_toggl_project_data()
		self.define_preset_date_bounds()

		tk.Tk.__init__(self, *args, **kwargs)

		tk.Tk.wm_title(self, "Toggl Reporting")

		container = ttk.Frame(self)
		container.pack(side="top", fill="both", expand=True)
		container.grid_rowconfigure(0, weight=1)
		container.grid_columnconfigure(0, weight=1)

		self.frames = {}

		frame = StartPage(container, self)
		self.frames[StartPage] = frame
		frame.grid(row=0, column=0, sticky='nsew')

		"""
		for F in (StartPage):
			frame = F(container, self)

			self.frames[F] = frame

			frame.grid(row=0, column=0, sticky="nsew")
		"""

		self.show_frame(StartPage)

	def show_frame(self, cont):
		frame=self.frames[cont]
		frame.tkraise()

	# Establish the connection to the TogglAPI, and collect the project data.
	def connect_to_toggl(self):
		self.toggl = Toggl()
		self.toggl.setAPIKey(config.API_KEY)
	
	# Get information about the user's projects from Toggl	
	def get_toggl_project_data(self):
		self.user_data = self.toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")

		project_data 	  = self.remove_empty_projects(self.user_data['data']['projects'])
		project_data_dict = {project_data[i]['name']: project_data[i] for i in range(0, len(project_data))}

		self.master_project_list = project_data_dict # Unchanging "master" list
		self.project_list 		 = project_data_dict # List of active projects to be displayed in the graph

	# Return a version of the project list, where all projects without any tracked hours are removed.
	# (This also removes projects which have been deleted via Toggl, but are still retrieved via the API)
	def remove_empty_projects(self, project_list):
		to_delete = []
		for i in range(0, len(project_list)):
			if not 'actual_hours' in project_list[i]:
				to_delete.append(i)

		for i in sorted(to_delete, reverse=True):
			del project_list[i]

		return project_list

	def define_preset_date_bounds(self):
		year = 365
		month = 30

		self.preset_date_bounds = {
			'Past Week': 	 7,
			'Past Month': 	 month,
			'Past 6 Months': month*6,
			'Past year': 	 year,
			'Past 2 years':  year*2,
			'Past 5 years':  year*5,
			'Custom':0
		}

	# Make a request to Toggl to get a report of all data from a given time frame.
	def get_report(self, params):
		data = {
		    'workspace_id': config.WORKSPACE_ID,
		    'since': params['start'],
		    'until': params['end'],
		}

		return self.toggl.getDetailedReportCSV(data)

	def is_valid_project(self, project):
		if project in self.project_list:
			return True
		else:
			return False

	def main_sequence(self, params, report):
		day = self.get_day()
		day = self.populate_day(day, report)

		self.create_graph(day)

	# Return an dictionary containing projects with minutes set to zero.
	def get_day(self):
		minutesInDay = 60*24
		day = {}
		emptyDay = {}

		for i in range (0, minutesInDay+1):
			emptyDay[i] = 0

		for project in self.project_list:
			day[project] = emptyDay.copy()

		return day

	# Populate the day dictionary with data from the report.
	def populate_day(self, day, report):
		with open (report.name, 'r') as file:
			reader = csv.DictReader(file)
			for row in reader:
				
				# Skipping header rows from merged csv.
				if row['Email'] == 'Email':
					continue

				startMinutes = self.getTimeInMinutes(row['Start time'])
				duration = self.getTimeInMinutes(row['Duration'])

				project = row['Project']

				if not self.is_valid_project(project):
					continue

				for i in range (startMinutes+1, startMinutes+duration+1):
					
					targetMinute = i

					if targetMinute >= 1440:
						targetMinute = abs(1440-i)

					day[project][targetMinute] += 1
			
		return day

	def getTimeInMinutes(self, time):
		split = re.split(':', time)

		hours = int(split[0])
		minutes = int(split[1])

		minutes += 60*hours

		return minutes

	def create_graph(self, day):
		for project_name in self.project_list:

			hex_color = self.project_list[project_name]['hex_color']

			plt.plot(list(day[project_name].keys()), list(day[project_name].values()), label=project_name, color=hex_color)

		plt.ylabel('Frequency')

		positions = []
		labels = []

		for i in range(0, 24):
			positions.append(i*60)

			time = str(i) + ':00'

			if len(time) < 5:
				time = '0' + time

			labels.append(time)

		plt.xticks(positions, labels)

		plt.grid()

		plt.legend()

		plt.show()


# StartPage Class -------------------------------------------------------------------------------------------
class StartPage(tk.Frame):

	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent)
		self.controller = controller

		self.create_custom_time_input()
		self.create_time_frame_select()
		self.create_projects_select()
		self.create_create_graph_button()

	# Create the frame for the input of custom time bounds.
	def create_custom_time_input(self):
		self.custom_time_input_frame = LabelFrame(self, text="Custom Time Frame", padx=10, pady=10)

		self.start_label = ttk.Label(self.custom_time_input_frame, text="Start Date:")
		self.start_label.grid(row=0, column=0, padx=10, pady=10)

		self.start_select = DateEntry(self.custom_time_input_frame)
		self.start_select.grid(row=0, column=1, padx=10, pady=10)

		self.end_label = ttk.Label(self.custom_time_input_frame, text="End Date:")
		self.end_label.grid(row=1, column=0, padx=10, pady=10)

		self.end_select = DateEntry(self.custom_time_input_frame)
		self.end_select.grid(row=1, column=1, padx=10, pady=10)

	# Create the input selector for the time frame.
	def create_time_frame_select(self):
		time_frame_label = ttk.Label(self, text="Time Frame:")
		time_frame_label.grid(row=1, column=0, padx=10, pady=10)

		self.time_frame_select = Listbox(self, selectmode=SINGLE, exportselection=False)

		for i in self.controller.preset_date_bounds:
			self.time_frame_select.insert(END, i)

		self.time_frame_select.bind('<<ListboxSelect>>', self.check_if_custom_time_frame_selected)

		self.time_frame_select.grid(row=1, column=1, padx=10, pady=10)

	def create_projects_select(self):
		self.project_selector_frame = LabelFrame(self, text="Projects", padx=10, pady=10)

		master_project_list = self.controller.master_project_list
		
		selector_list = {}
		for project_name in master_project_list:

			selector_list[project_name] = master_project_list[project_name]['actual_hours']

		self.project_selector = Listbox(self.project_selector_frame, selectmode=MULTIPLE, exportselection=False)

		for project_name in master_project_list:
			self.project_selector.insert(END, project_name)

		self.project_selector.grid(row=0, column=0)

		self.project_selector_frame.grid(row=1, column=3, padx=10, pady=10)

	def create_create_graph_button(self):
		create_graph_button = ttk.Button(self, text="Create Graph", command=self.confirm_date_selection)
		create_graph_button.grid(row=2, column=0, padx=10, pady=10)


	# Check if the user has selected a custom time frame. If so, display the custom time input frame.
	def check_if_custom_time_frame_selected(self, callback_value):
		custom_selected = self.using_custom_date_bounds()
		self.toggle_custom_date_input(custom_selected)

	# Return True/False for whether the user has selected a custom time frame.
	def using_custom_date_bounds(self):
		return self.time_frame_select.select_includes(END)

	# Hide/show the custom date input box	
	def toggle_custom_date_input(self, value):
		if value == True:
			self.custom_time_input_frame.grid(row=1, column=2, padx=10, pady=10)
		else:
			self.custom_time_input_frame.grid_forget()



	def confirm_date_selection(self):
		self.assign_chosen_projects()

		date_bounds = self.get_date_bounds()

		# Split the request into several with a max length of one year. (Toggl API only allows reports of max 1 year length)
		split_bounds = self.split_date_bounds(date_bounds)

		# A list of all the reports we gather from Toggl. (Max 1 year each)
		reports = []

		for bounds in split_bounds:
			params = {
				'start': bounds['start'],
				'end': bounds['end']
			}

			reports.append(app.get_report(params))

		joined_report = self.join_reports(reports)

		app.main_sequence(params, joined_report)

	# Assign the user's chosen projects to the controller's active project list.
	def assign_chosen_projects(self):
		chosen_projects = [self.project_selector.get(idx) for idx in self.project_selector.curselection()]

		self.controller.project_list = {} # Emptying the project list

		for project_name in chosen_projects:
			self.controller.project_list[project_name] = self.controller.master_project_list[project_name]

		self.controller.show_frame(StartPage)


	# Return the start and end date for the bounds that the user has selected.
	def get_date_bounds(self):
		if self.using_custom_date_bounds():
			dates = {
				'start': self.start_select.get_date(),
				'end': self.end_select.get_date()
			}
		else:
			string_selected = self.time_frame_select.get(self.time_frame_select.curselection())
			day_count = self.controller.preset_date_bounds[string_selected]

			dates = {
				'start': datetime.now() - timedelta(days=day_count),
				'end': datetime.now()
			}

		return dates

	# Return a list containing a series of bounds, each of at most 1 year long.
	def split_date_bounds(self, bounds):
		span = self.get_report_span(bounds['start'], bounds['end'])

		number_of_years = math.ceil(span/365)

		bounds = []

		for year in range(number_of_years):
			remaining_days_after_subtraction = span - 365
			
			start = datetime.now() - timedelta(days = span)

			if (remaining_days_after_subtraction > 0):
				span = remaining_days_after_subtraction	
				end = datetime.now() - timedelta(days = span + 1) #(Plus 1 so we don't get an overlap at the edge of the bounds)
			else:
				end = datetime.now()

			bounds.append(
				{
					'start': start,
					'end': end
				}
			)

		return bounds

	# Return the length of time that a report covers. (In days)
	def get_report_span(self, start, end):
		span = end - start
		return span.days

	# Join the given reports together, saving them as a temporary csv file.
	def join_reports(self, reports_list):
		filename = 'test.csv'

		test = ''

		temporary_csv_file = tempfile.NamedTemporaryFile()

		for report in reports_list:

			with open(temporary_csv_file.name, 'ab') as csv:
				csv.write(report)

		return temporary_csv_file

app = TogglReportingApp()

app.mainloop()