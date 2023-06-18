import PySimpleGUI as sg

x=5
y=10
yaw=90
sg.theme('DarkAmber')   # Add a touch of color
# All the stuff inside your window.
layout = [[sg.Text('Some text on Row 1')],
          [sg.Text('Last pose'), sg.Text(x), sg.Text(y), sg.Text(yaw)],
          [sg.Text('pose001'), sg.Text(x), sg.Text(y), sg.Text(yaw), sg.Button('Teach'), sg.Button('Set')],
          [sg.Text('Enter something on Row 2'), sg.InputText()],
          [sg.Button('Ok'), sg.Button('Cancel')]]

# Create the Window
window = sg.Window('Window Title', layout)
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
        break
    print('You entered ', values[0])

window.close()
