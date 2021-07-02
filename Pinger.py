#!/usr/bin/python
import sqlite3
import PySimpleGUI as sg
import platform
import os
import asyncio
import subprocess
import DBConnection
import threading
import time

version = "v1.0.0"
sg.theme('Dark')

hosts = ["", "", "", ""]

# Static Variables
class PingVar(threading.Thread):
    totalCount = 0
    pingThread = None
    
# Table for Pings       IP   UP DOWN
pingTable = [["Gateway",0,0,0],["Usable",0,0,0],["LAN",0,0,0],["Switch",0,0,0]]

# Stop all pinging
def stopPinging(window):
    global pinging
    window.Element('-STATUS-').Update(value=("Idle"))
    pinging = False
    if(PingVar.pingThread != None and PingVar.pingThread.is_alive()):
        PingVar.pingThread.join(timeout=0.05)
        PingVar.pingThread = None

# Ping the list of hosts
def ping(packet_size, window):
    DETACHED_PROCESS = 0x00000008
    totalCount_arg = '-n' if platform.system().lower()=='windows' else '-c'
    packet_arg = '-l' if platform.system().lower() == 'windows' else '-s'
    timeout_arg = '-w' if platform.system().lower() == 'windows' else '-W'
    # Results of pings         UP DOWN
    results = [[0,0],[0,0],[0,0],[0,0]]
    response = None

    i = 0
    for i in range(len(hosts)):
        response = subprocess.call('ping ' + totalCount_arg + ' 1 ' + timeout_arg + ' 1 ' + packet_arg + ' ' + packet_size + ' ' + hosts[i], creationflags=DETACHED_PROCESS)

        if(response == 0):
            results[i][0] += 1
        else:
            results[i][1] += 1

        if hosts[i][-3:] == '254':
            time.sleep(3)
        i += 1

    return window.write_event_value('-THREAD-', results)

def updateTable(packetSize, window):
    if(PingVar.totalCount < 200):
        PingVar.pingThread = PingVar(target=ping, args=(packetSize, window))
        PingVar.pingThread.start()  
        PingVar.totalCount += 1
    else:
        stopPinging(window)

def gui():
    # Left column for the branch list
    branch_list_column = [
        [sg.Menu([['File', ['Exit']],['Edit',['Modify Branches']], ['Help', 'About']])],
        [sg.Text("Branches")],
        [sg.Listbox(values=DBConnection.branchList, enable_events=True, size=(30, 20), key="-BRANCH LIST-", background_color='white', text_color='black')],
    ]

    packet_size = [*range(1,101)]
    # Right column for the pinger
    ping_viewer_column = [
        [sg.Table(values=pingTable,
                  enable_events=True,
                  num_rows=4,
                  headings=["Device","IP Address","Up", "Down"],
                  key="-PING LIST-",
                  col_widths=[10,12,5,5],
                  auto_size_columns=False,
                  background_color='white',
                  text_color='black',
                  hide_vertical_scroll=True)],
        [sg.Text("Status: "), sg.StatusBar(text="Idle", key="-STATUS-"),
         sg.Text("Packet Size: ", justification='center'),
         sg.Spin(initial_value=32, key="-PACKET SIZE-", values=packet_size, readonly=True, background_color="white", text_color="black")],
         [sg.Button(button_text="Ping", key="-PING BUTTON-", enable_events=True, button_color='green', focus=True),
         sg.Button(button_text="Stop", key="-STOP BUTTON-", enable_events=True, button_color='red')]
    ]

    # Layout for the right column of the window
    branding_column = [
        [sg.Image('logo.png')],
        [sg.Frame(title="Output",layout=ping_viewer_column, element_justification='center')]
    ]

    # Layout for the ping output table
    pinger_layout = [[sg.Column(branch_list_column), sg.VSeperator(), sg.Column(branding_column, element_justification='center')]]

    # Layout for the window
    layout = [
        [sg.TabGroup([[sg.Tab('Branch Pinger', pinger_layout)]])]
    ]

    # Layout for Properties page
    properties_layout = [
        [sg.Image('logo.png')],
        [sg.Text("Pinger version " + version)],
        [sg.Text("Developed and Tested by Patrick Cook.")],
        [sg.Text("Only for internal use.")]
    ]

    # Layout for Timeout window when left pinging for a certain amount of time
    timeout_layout = [
        [sg.Text("Max branch ping time exceeded, ping has been stopped.")]
    ]

    # Window Title
    window = sg.Window("Pinger " + version, layout, element_justification="center")
    properties = sg.Window("About", properties_layout, element_justification="center", disable_minimize=True, keep_on_top=True)
    timeout = sg.Window("Ping Timeout", timeout_layout, element_justification="center", disable_minimize=True, keep_on_top=True)

    global pinging
    DBConnection.openDatabase()
    selected = False
    process = None
    PingVar.totalCount = 0
    packetSize = 32

    while True:
        event, values = window.read(timeout=100)
        if event == "Exit" or event == sg.WIN_CLOSED: # Ends the window and closes the database connection
            DBConnection.conn.close()
            break
        elif event == "-BRANCH LIST-": # Opens the pinger for the selected branch
            selected = True
            stopPinging(window)
            window.Element('-PING LIST-').update(row_colors=[[0, 'black', 'white'], [1,'black','white'], [2,'black', 'white'], [3,'black', 'white']])
            selectedBranch = str(values["-BRANCH LIST-"]).replace("[","").replace("]","")
            hosts[0] = str(DBConnection.conn.execute("SELECT GATEWAY from Branches WHERE BRANCH = " + selectedBranch).fetchone()).replace("(", "").replace(")","").replace("\'","")[:-1]
            hosts[1] = str(DBConnection.conn.execute("SELECT USABLE from Branches WHERE BRANCH = " + selectedBranch).fetchone()).replace("(", "").replace(")","").replace("\'","")[:-1]
            hosts[2] = str(DBConnection.conn.execute("SELECT LAN from Branches WHERE BRANCH = " + selectedBranch).fetchone()).replace("(", "").replace(")","").replace("\'","")[:-1]
            hosts[3] = str(DBConnection.conn.execute("SELECT SWITCH from Branches WHERE BRANCH = " + selectedBranch).fetchone()).replace("(", "").replace(")","").replace("\'","")[:-1]
            window.Element('-PING LIST-').update(values=[
                ["Gateway", hosts[0], 0, 0],
                ["Usable", hosts[1], 0, 0],
                ["LAN", hosts[2], 0, 0],
                ["Switch", hosts[3], 0, 0]])
            
        elif event == "-PING BUTTON-":
            # Ping Operation
            if selected is False:
                continue
            if pinging is False:
                pinging = True
            else:
                stopPinging(window)
            PingVar.totalCount = 0
            window.Element('-STATUS-').Update(value=("Pinging..."))
            packetSize = str(window.Element('-PACKET SIZE-').get())

            updateTable(packetSize, window)

        elif event == "-THREAD-":
            results = values[event]
            i = 0
            j = 2
            color = ['', '', '', '']
            if(PingVar.pingThread == None):
                pass
            else:
                for i in range(len(results)):
                    for j in range(len(results[0])): 
                        if(pingTable[i][j] == results[i][j == j - 2]):
                            color[i] = 'red'
                        else:
                            color[i] = 'green'
                        j += 1
                    i += 1

                currentPingTable = window.Element('-PING LIST-').get()
                window.Element('-PING LIST-').update(values=[
                                    ["Gateway", hosts[0], currentPingTable[0][2] + results[0][0], currentPingTable[0][3] + results[0][1]],
                                    ["Usable", hosts[1], currentPingTable[1][2] + results[1][0], currentPingTable[1][3] + results[1][1]],
                                    ["LAN", hosts[2], currentPingTable[2][2] + results[2][0], currentPingTable[2][3] + results[2][1]],
                                    ["Switch", hosts[3], currentPingTable[3][2] + results[3][0], currentPingTable[3][3] + results[3][1]]])
        
                window.Element('-PING LIST-').update(row_colors=[
                                                    [0, color[0]],
                                                    [1, color[1]],
                                                    [2, color[2]],
                                                    [3, color[3]]])

                if(PingVar.pingThread != None and PingVar.pingThread.is_alive()):
                    PingVar.pingThread.join(timeout=0.05)
                if(PingVar.totalCount < 200):
                    updateTable(packetSize, window)
                else:
                    stopPinging(window)
                    timeout.read()
                                    
        elif event == "-STOP BUTTON-":
            stopPinging(window)
            
        elif event == "About":
            # Open Properties Menu
            while True:
                propevent, propValues = properties.read()
                if propevent == "Exit" or propevent == sg.WIN_CLOSED:
                    properties.close()
                    break

        elif event == "Ping Timeout":
            # Open Ping Timeout window
            while True:
                timeevent, sqlTimeout = timeout.read()
                if timeevent == "Exit" or timeevent == sg.WIN_CLOSED:
                    timeout.close()
                    break
        
    # Closes all open resources for the program
    window.close()

if __name__ == '__main__':
    gui()
