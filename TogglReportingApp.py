import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkcalendar import Calendar, DateEntry
from toggl.TogglPy import Toggl

import csv
import re

import matplotlib.pyplot as plt

import config

LARGE_FONT = ("Verdana", 12)

class TogglReportingApp(tk.Tk):

	def __init__(self, *args, **kwargs):
		tk.Tk.__init__(self, *args, **kwargs)

		tk.Tk.wm_title(self, "Toggl Reporting")

		container = ttk.Frame(self)
		container.pack(side="top", fill="both", expand=True)
		container.grid_rowconfigure(0, weight=1)
		container.grid_columnconfigure(0, weight=1)

		self.frames = {}

		self.connect_to_toggl()

		for F in (StartPage, ProjectsPage):
			frame = F(container, self)

			self.frames[F] = frame

			frame.grid(row=0, column=0, sticky="nsew")

		self.show_frame(StartPage)

		self.projectList = ['Film/TV', 'Maths', 'Reading', 'Real Life Social', 'Physics', 'Coding', 'Johanna']

		

	def show_frame(self, cont):
		frame=self.frames[cont]
		frame.tkraise()


	def connect_to_toggl(self):
		self.toggl = Toggl()
		self.toggl.setAPIKey(config.API_KEY)
		
		self.user_data = self.toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")

		project_data = self.user_data['data']['projects']

		projects = {}

		for p in project_data:
			project_name = p['name']

			projects[project_name] = {
				'color': p['color'],
				'status': True
			}

		self.projects = projects

	def get_report(self, params):
		data = {
		    'workspace_id': config.WORKSPACE_ID,
		    'since': params['start'],
		    'until': params['end'],
		}

		self.toggl.getDetailedReportCSV(data, "report.csv")

	def getTimeInMinutes(self, time):
		split = re.split(':', time)

		hours = int(split[0])
		minutes = int(split[1])

		minutes += 60*hours

		return minutes

	def isValidProject(self, project):
		if project in self.projectList:
			return True
		
		return False

	# Return an dictionary containing projects with minutes set to zero.
	def get_day(self):
		minutesInDay = 60*24
		day = {}
		emptyDay = {}

		for i in range (0, minutesInDay+1):
			emptyDay[i] = 0

		for project in self.projectList:
			day[project] = emptyDay.copy()

		return day

	# Populate the day dictionary with data from the report.
	def populate_day(self, day):
		with open ('report.csv', 'r') as file:
			reader = csv.DictReader(file)
			for row in reader:
				startMinutes = self.getTimeInMinutes(row['Start time'])
				duration = self.getTimeInMinutes(row['Duration'])

				project = row['Project']

				if not self.isValidProject(project):
					continue
			
				#if not project in day.keys():
					#day[project] = {}

				#print(day)

				#if not project == 'Online Social':
				#	continue

				for i in range (startMinutes+1, startMinutes+duration+1):
					
					targetMinute = i

					if targetMinute >= 1440:
						targetMinute = abs(1440-i)

					day[project][targetMinute] += 1
					#day['Total'][targetMinute] += 1
			
		#for project in day:
			#del day[project][1440]# Remove this because otherwise we're considering midnight twice.

		return day

	def main_sequence(self, params):
		self.connect_to_toggl()

		day = self.get_day()

		day = self.populate_day(day)

		self.create_graph(day)

	def create_graph(self, day):
		for project in self.projectList:

			plt.plot(list(day[project].keys()), list(day[project].values()), label=project)

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


class StartPage(tk.Frame):

	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent)

		start_label = ttk.Label(self, text="Start Date:")
		start_label.grid(row=0, column=0, padx=10, pady=10)

		start_select = DateEntry(self)
		start_select.grid(row=0, column=1, padx=10, pady=10)

		end_label = ttk.Label(self, text="End Date:")
		end_label.grid(row=1, column=0, padx=10, pady=10)

		end_select = DateEntry(self)
		end_select.grid(row=1, column=1, padx=10, pady=10)

		select_projects_button = ttk.Button(self, text="Projects",
								command=lambda: controller.show_frame(ProjectsPage))
		select_projects_button.grid(row=0, column=2, padx=10, pady=10)



		create_graph_button = ttk.Button(self, text="Create Graph",
							command=self.confirm_date_selection)
		create_graph_button.grid(row=2, column=0, padx=10, pady=10)



		self.start_select = start_select
		self.end_select = end_select

	def select_projects(self):
		app.select_project()

	def confirm_date_selection(self):

		params = {
			'start': self.start_select.get_date(),
			'end': self.end_select.get_date()
		}

		app.get_report(params)

		app.main_sequence(params)

class ProjectsPage(tk.Frame):
	def __init__(self, parent, controller):
		tk.Frame.__init__(self, parent)

		projects = controller.projects

		self.listbox = Listbox(self, selectmode=EXTENDED)

		for p in projects:
			self.listbox.insert(END, p)

		self.listbox.pack()


		confirm_projects_button = Button(self, text="Confirm", command=lambda: self.confirm_project_selection(controller))
		confirm_projects_button.pack()

	def confirm_project_selection(self, controller):
		chosen_projects = [self.listbox.get(idx) for idx in self.listbox.curselection()]

		controller.projectList = chosen_projects

		controller.show_frame(StartPage)

app = TogglReportingApp()

app.mainloop()