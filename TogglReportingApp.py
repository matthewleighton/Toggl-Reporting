"""
#To Do List:
- !!! Refactor code to join together project and client functions. Much of this is the same, and can be combined !!!
- Add "No Client" client, to include projects with no client. Currently they're being excluded.
- Ability to show multiple graphs at once
- Rename "More Settings" button to "Grouping Settings"
- Add title to graph, showing timespan.
- Search by client
- Some kind of search via tags
- Ability to save/load different configurations of settings
- Ability to manually enter Toggl info to login, and switch between accounts.
"""
from startpage import StartPage

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
from operator import itemgetter
import pprint

LARGE_FONT = ("Verdana", 12)

# TogglReportingApp Class -------------------------------------------------------------------------------------------
class TogglReportingApp(tk.Tk):

	def __init__(self, *args, **kwargs):
		self.toggl_setup()
		self.tkinter_setup(*args, **kwargs)

	def toggl_setup(self):
		self.connect_to_toggl()
		self.get_toggl_project_data()
		self.get_toggl_report_data()
		self.define_preset_date_bounds()
		
		self.group_by = 'Project'
		self.description_groupings = []
		self.date_bounds = {}

	def tkinter_setup(self, *args, **kwargs):
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

		client_data 	 = self.user_data['data']['clients']
		client_data_dict = {client_data[i]['name']: client_data[i] for i in range(0, len(client_data))}

		self.master_client_list  = client_data_dict # Unchanging "master" list
		self.client_list 		 = client_data_dict # List of active projects to be displayed in the graph

		# Assigning clients to projects.
		for client in client_data:
			client_id = client['id']
			client_name = client['name']

			for project_name in self.master_project_list:				
				if not 'cid' in self.master_project_list[project_name]:
					self.master_project_list[project_name]['client'] = False
				elif self.master_project_list[project_name]['cid'] == client_id:
					self.master_project_list[project_name]['client'] = client_name

		#self.project_list = list(self.master_project_list.keys())
		self.project_list = []

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

	def get_toggl_report_data(self):
		years = 1

		date_bounds = {
				'start': datetime.now() - timedelta(days=365*years), #Get reports from the last n years.
				'end': datetime.now()
			}

		split_bounds = self.split_date_bounds(date_bounds)

		# A list of all the reports we gather from Toggl. (Max 1 year each)
		reports = []

		for bounds in split_bounds:
			params = {
				'start': bounds['start'],
				'end': bounds['end']
			}

			reports.append(self.get_report(params))

		self.full_toggl_report = self.join_reports(reports)

	def define_preset_date_bounds(self):
		year = 365
		month = 30

		self.preset_date_bounds = {
			'Past Week': 	 7,
			'Past Month': 	 month,
			'Past 6 Months': month*6,
			'Past Year': 	 year,
			'Past 2 Years':  year*2,
			'Past 5 Years':  year*5,
			'Custom':0
		}

	def set_group_by(self, group_by):
		self.group_by = group_by

	# Make a request to Toggl to get a report of all data from a given time frame.
	def get_report(self, params):
		data = {
		    'workspace_id': config.WORKSPACE_ID,
		    'since': params['start'],
		    'until': params['end'],
		}

		return self.toggl.getDetailedReportCSV(data)

	def is_included_project(self, project):
		if project in self.project_list:
			return True
		else:
			return False

	def is_included_client(self, client):
		if client in self.client_list:
			return True
		else:
			return False

	def main_sequence(self):
		self.update_project_data()
		self.update_client_data()
		self.update_description_restrictions()

		report = self.full_toggl_report

		day = self.get_day()
		day = self.populate_day(day, report)

		self.create_graph(day)

	def update_project_data(self):
		user_selection = self.project_list
		self.project_list = {}

		for project_name in user_selection:
			self.project_list[project_name] = self.master_project_list[project_name]

	def update_client_data(self):
		user_selection = self.client_list
		self.client_list = {}

		for client_name in user_selection:
			self.client_list[client_name] = self.master_client_list[client_name]

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

		bounds.reverse() # We reverse the order, because we need reverse-chronological in order to signal when to stop the populate_day function.

		return bounds

	# Return the length of time that a report covers. (In days)
	def get_report_span(self, start, end):
		span = end - start
		return span.days

	# Join the given reports together, saving them as a temporary csv file.
	def join_reports(self, reports_list):
		temporary_csv_file = tempfile.NamedTemporaryFile()

		for report in reports_list:

			with open(temporary_csv_file.name, 'ab') as csv:
				csv.write(report)

		return temporary_csv_file

	def update_description_restrictions(self):
		self.allowed_descriptions = []
		self.excluded_descriptions = []

		for i in self.description_search_list:
			description_row = self.description_search_list[i]
			value 			= description_row['entry'].get().lower()
			excluded 		= bool(description_row['exclude_checkbox_value'].get())

			if excluded:
				self.excluded_descriptions.append(value)
			else:
				self.allowed_descriptions.append(value)

		# If there are no specifically allowed descriptions, say that an empty string is allowed. (Otherwise we'll return nothing).
		if not self.allowed_descriptions:
			self.allowed_descriptions = ['']

	# Return an dictionary containing projects with minutes set to zero.
	def get_day(self):
		minutesInDay = (60*24)-1 #Subtract 1 because it is zero indexed. Minute 1440 is the following midnight, which will be empty.
		day = {}
		emptyDay = {}

		for i in range (0, minutesInDay+1):
			emptyDay[i] = 0

		if self.group_by == 'Project':
			for project in self.project_list:
				day[project] = emptyDay.copy()
		if self.group_by == 'Description':
			for grouping in self.description_groupings:
				day[grouping['title']] = emptyDay.copy()
		if self.group_by == 'Timeframe':
			for timeframe in self.date_bounds.values():
				day[timeframe['name']] = emptyDay.copy()
		if self.group_by == 'None':
			day = emptyDay

		return day

	# Return the earliest date from a set of timeframes.
	def find_earliest_date_bound(self, timeframes):
		earliest = datetime.today()

		for date_bounds_pair in self.date_bounds.values():
			start = date_bounds_pair['start']

			if start < earliest:
				earliest = start

		return earliest

	# Populate the day dictionary with data from the report.
	def populate_day(self, day, report):
		earliest_date_bound = self.find_earliest_date_bound(self.date_bounds)

		with open (report.name, 'r') as file:
			reader = csv.DictReader(file)
			for row in reader:

				print(row)

				try:
					entry_date = datetime.strptime(row['Start date'], '%Y-%m-%d')
				except ValueError:
					continue

				if entry_date < earliest_date_bound: # If the entry is earlier than our earliest date bound, we stop.
					break

				print(row)

				project 	= row['Project']
				description = row['Description']
				client 		= row['Client']
				
				# Skipping header rows from merged csv.
				if row['Email'] == 'Email':
					continue

				if not self.is_included_project(project):
					continue

				if not self.is_included_client(client):
					continue

				matched_timeframes = []

				# Skipping entries which are outside of our date bounds.
				within_bounds = False
				for date_bounds_pair in self.date_bounds.values():
					if date_bounds_pair['start'] <= entry_date <= date_bounds_pair['end']:
						within_bounds = True

						if self.group_by == 'Timeframe':
							timeframe_name = date_bounds_pair['name']
							if not timeframe_name in matched_timeframes:
								matched_timeframes.append(timeframe_name)


				if not within_bounds:
					continue

				description_match = False

				if self.group_by == 'Description':
					matched_description_groups = []

					for description_grouping in self.description_groupings:
						for user_description in description_grouping['descriptions']:
							if user_description in description.lower():
								description_match = True
								grouping_title = description_grouping['title']
								if not grouping_title in matched_description_groups:
									matched_description_groups.append(grouping_title)
				else:
					for allowed_description in self.allowed_descriptions:
						if allowed_description in description.lower():
							description_match = True
							break

					for excluded_description in self.excluded_descriptions:
						if excluded_description in description.lower():
							description_match = False

					if not description_match:
						continue

				startMinutes = self.getTimeInMinutes(row['Start time'])
				duration = self.getTimeInMinutes(row['Duration'])

				for i in range (startMinutes+1, startMinutes+duration+1):
					
					targetMinute = i

					if targetMinute >= 1440:
						targetMinute = abs(1440-i)

					if self.group_by == 'Project':
						day[project][targetMinute] += 1
					elif self.group_by == 'Description':
						for description_group in matched_description_groups:
							day[description_group][targetMinute] += 1
					elif self.group_by == 'Timeframe':
						for timeframe in matched_timeframes:
							day[timeframe][targetMinute] += 1
					elif self.group_by == 'None':
						day[targetMinute] += 1

		day = self.remove_empty_categories(day)

		return day

	# Remove all the categories from a day which have zero minutes tracked over the time span.
	def remove_empty_categories(self, day):
		empty_categories = []
		for category_name in day:
			if all(value == 0 for value in day[category_name].values()):
				empty_categories.append(category_name)
		
		for category_name in empty_categories:
			del day[category_name]

		return day

	def getTimeInMinutes(self, time):
		split = re.split(':', time)

		hours = int(split[0])
		minutes = int(split[1])

		minutes += 60*hours

		return minutes

	def get_minutes_since_midnight(self):
		now = datetime.now()
		midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
		minutes = (now - midnight).seconds/60

		return minutes

	def create_graph(self, day):
		if self.group_by == 'Project':
			for project_name in day:

				hex_color = self.project_list[project_name]['hex_color']

				plt.plot(list(day[project_name].keys()), list(day[project_name].values()), label=project_name, color=hex_color)
		elif self.group_by == 'Description':
			for grouping in self.description_groupings:
				title = grouping['title']
				plt.plot(list(day[title].keys()), list(day[title].values()), label=title)
		elif self.group_by == 'Timeframe':
			for timeframe_name in day:
				plt.plot(list(day[timeframe_name].keys()), list(day[timeframe_name].values()), label=timeframe_name)
		elif self.group_by == 'None':
			plt.plot(list(day.keys()), list(day.values()))

		plt.ylabel('Frequency')

		positions = []
		labels = []

		for i in range(0, 24):
			positions.append(i*60)

			time = str(i) + ':00'

			if len(time) < 5:
				time = '0' + time

			labels.append(time)

		if self.highlight_current_time.get():
			minutes_since_midnight = self.get_minutes_since_midnight()
			plt.axvline(x=minutes_since_midnight)

		plt.xticks(positions, labels)

		plt.grid()

		plt.legend()

		mng = plt.get_current_fig_manager()
		mng.full_screen_toggle()

		plt.show()

app = TogglReportingApp()

app.mainloop()