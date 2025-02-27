# inspired from PyMoDAQ project : https://github.com/PyMoDAQ/PyMoDAQ

from typing import Dict, List, Any

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType

from serial.tools.list_ports import comports
from apscheduler.schedulers.background import BackgroundScheduler

MAX_SLAVE_NUMBER = 6

available_ports = []
for port in comports():
    available_ports.append(port.device)

dict_baudrates = {'4800': 0, '9600': 1, '19200': 2, '38400': 3, '57600':4, '115200': 5}

dict_parities = {'E': 0, 'O': 1, 'N': 2}    

dict_stopbits = {'0': 0, '1': 1, '2': 2}

link_interfaces = [
    {'title': 'Serial:', 'name': 'serial', 'type': 'group', 'children': [
        {'title': 'Serial Type:', 'name': 'serial_type', 'type': 'list', 'values': {'RS232': 0, 'RS485': 1}, 'value': 1},
        {'title': 'COM Port:', 'name': 'comport', 'type': 'list', 'values': available_ports},
        {'title': 'Baud Rate:', 'name': 'baudrate', 'type': 'list', 'values': dict_baudrates, 'value':5},
        {'title': 'Byte Size:', 'name': 'bytesize', 'type': 'list', 'values': [7, 8], 'value': 8},
        {'title': 'Parity:', 'name': 'parity', 'type': 'list', 'values': dict_parities, 'value': 1},
        {'title': 'Stop bits', 'name': 'stopbits', 'type': 'list', 'values': dict_stopbits, 'value': 1},
        {'title': 'Read Timeout', 'name': 'read_timeout', 'type': 'float', 'value': 0.1, 'dec': True, 'min': 0, 'suffix': 's', 'siPrefix': True},
        ]},
    {'title': 'TCP/IP:', 'name': 'tcpip', 'type': 'group', 'children': [
        {'title': 'IP address:', 'name': 'ip_address', 'type': 'str', 'value': '10.47.0.39'},
        {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': 6341, 'decimals': 6},
        ]},
    ]
               
interface_connect = [{'title': 'Connect to device:', 'name': 'connect_device', 'type': 'action'},
               {'title': 'Connected?:', 'name': 'device_connected', 'type': 'bool', 'value': False, 'readonly': True},]

save_restore_params = [{'name': 'Save/Restore functionality', 'type': 'group', 'expanded': False, 'children': [
    {'name': 'Save State', 'type': 'action', 'visible': True},
    {'name': 'Restore State', 'type': 'action', 'children': [
        {'name': 'Add missing items', 'type': 'bool', 'value': True},
        {'name': 'Remove extra items', 'type': 'bool', 'value': True},
        ]},]},]

class InterfaceParameter(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'bool'
        opts['value'] = True
        pTypes.GroupParameter.__init__(self, **opts)
                
        self.addChild({'title': 'Link Interface:', 'name': 'link_interface', 'type': 'list', 'values': ['Serial', 'TCP/IP']})
        self.addChild(interface_connect[0])
        self.addChild(interface_connect[1])
        
        self.a = self.param('link_interface')
        self.a.sigValueChanged.connect(self.linkInterfaceChanged)
        
        if self.a.value() == 'Serial':
            self.a.addChild(link_interfaces[0])
        else:
            self.a.addChild(link_interfaces[1])
        
    def linkInterfaceChanged(self):
        #pass
        self.a.clearChildren()
        if self.a.value() == 'TCP/IP':
            self.a.addChild(link_interfaces[1])
        else:
            self.a.addChild(link_interfaces[0])

main_settings_params = [
    {'title': 'Main Settings', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
        {'title': 'Controller ID:', 'name': 'controller_ID', 'type': 'int', 'value': 0, 'default': 0, 'readonly': True},
        {'title': 'Grab data:', 'name': 'show_data', 'type': 'bool', 'value': False, },
        {'title': 'Line Color:', 'name': 'line_color', 'type': 'color', 'value': 'y', 'tip': "This is a color button"},
        {'title': 'Refresh Rate:', 'name': 'refresh_rate', 'type': 'float', 'value': 1, 'dec': True, 'step': 1, 'siPrefix': True, 'suffix': 'Hz'},
        {'title': 'Continuous saving:', 'name': 'continuous_saving_opt', 'type': 'bool', 'default': False,
         'value': False},
        InterfaceParameter(name='Device Interface'),
        ]},]

class ControllerParameterTree(QtWidgets.QWidget):
    def __init__(self, controller_params: List[Dict[str, Any]]) -> None:
        super(ControllerParameterTree, self).__init__()
        self.params = main_settings_params + controller_params + save_restore_params        
        self.setup_parametertree()
        
    def setup_parametertree(self):
        ## Create tree of Parameter objects
        self.settings = Parameter.create(name='params', 
                                         type='group', 
                                         children=self.params)
        
        self.settings.sigTreeStateChanged.connect(self.change)
        
        # Too lazy for recursion: 2 levels of children
        for child in self.settings.children():
            child.sigValueChanging.connect(self.valueChanging)
            for ch2 in child.children():
                ch2.sigValueChanging.connect(self.valueChanging)
                
        self.settings.param('main_settings', 
                            'Device Interface', 
                            'connect_device').sigActivated.connect(
                                self.init_controller)
        self.settings.param('Save/Restore functionality', 
                            'Save State').sigActivated.connect(self.save)
        self.settings.param('Save/Restore functionality', 
                            'Restore State').sigActivated.connect(
                                self.restore)

        ## Create ParameterTree widgets
        self.parametertree = ParameterTree()
        self.parametertree.setParameters(self.settings, showTop=False)
    
    def init_controller(self):
        """to reimplement in  subclass
        """   
        print("init_controller from superclass.")
        pass     
    
    def add_parametertree(self, parent:QtWidgets.QGridLayout=None):
        if parent == None:
            layout =  QtWidgets.QGridLayout()
            self.setLayout(layout)
            layout.addWidget(self.parametertree, 1, 0, 1, 1)
        else:
            parent.addWidget(self.parametertree)

    def grab_data(self):
        """to reimplement in subclass
        """        
        print('read pv...')
    
    def start_DAQ(self):      
        # test scheduler
        self.settings.child('main_settings', 'refresh_rate').setReadonly(True)
        wait_time = 1/self.settings.child('main_settings', 'refresh_rate').value()
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.grab_data, 'interval', seconds=wait_time)
        #scheduler.add_job(get_tg_sp, 'interval', seconds=0.2)
        self.scheduler.start()
            
    def stop_DAQ(self):
        self.scheduler.shutdown()
        self.settings.child('main_settings', 'refresh_rate').setReadonly(readonly=False)
                
    ## If anything changes in the tree, print a message
    def change(self, param, changes):
        # print("tree changes:")
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            # print('  parameter: %s'% childName)
            # print('  change:    %s'% change)
            # print('  data:      %s'% str(data))
            # print('  ----------')
            if childName == 'main_settings.show_data':
                self.start_DAQ() if data else self.stop_DAQ()

    def valueChanging(param, value):
        print("Value changing (not finalized): %s %s" % (param, value))
    
    def save(self):
        global state
        state = self.settings.saveState()
        
    def restore(self):
        global state
        add = self.settings['Save/Restore functionality', 'Restore State', 'Add missing items']
        rem = self.settings['Save/Restore functionality', 'Restore State', 'Remove extra items']
        self.settings.restoreState(state, addChildren=add, removeChildren=rem)

if __name__ == "__main__":
    import sys, os
    this_dir=os.path.dirname(os.path.abspath(__file__))
    # src_dir=os.path.dirname(this_dir)
    # sys.path.insert(1, src_dir)
    
    from utils import PrmsDetail
    
    def to_children(item_list):
        children=[]
        for item in item_list:
            default= 0 if item['default'] == 'Rated speed' else item['default']
            child={
                'title': item['function'].lower() + " "*4,
                'name': item['function'].lower().replace(' ', '_'),
                'type': 'float' if '.' in item['range'] else 'int', #TODO for key 'type': list or group if not continous values
                'default': float(default) if '.' in item['range'] else int(float(default)),
                'suffix': item['unit'], 
                'tip': item['description'].split('\n')[0],
                'readonly': False,
                'visible': False, # change with .setOpts(visible=True) 
            }
            children.append(child)
        return children
    
    prms_d=PrmsDetail()
    d=prms_d.read_detail()
    all_params = []
    for key, item in d.items():
        params={'title': key,
                'name': key.replace(' ', '_'), 
                'expanded': False,
                'type': 'group',
                'children': to_children(item),}
        all_params.append(params)
    
    list_aasd_settings = []
    for i in range(MAX_SLAVE_NUMBER):
        list_aasd_settings += [
            {
                'title': 'Servo '+str(i+1), 
                'name': 'servo_'+str(i+1), 
                'expanded': False, 
                'type': 'group', 
                'children': all_params
            }
        ]
    controller_params = [
        {'title': '6DOF Settings', 'name': 'device_settings', 'expanded': False, 'type': 'group', 'children': list_aasd_settings},
    ]
    
    app = QtWidgets.QApplication([])
    prmtt = ControllerParameterTree(controller_params)
    prmtt.add_parametertree()
    prmtt.show()

    ## test save/restore
    state = prmtt.settings.saveState()
    prmtt.settings.restoreState(state)
    
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec()



