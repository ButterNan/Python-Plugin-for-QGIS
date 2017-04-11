# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LeakDetection
                                 A QGIS plugin
 This plugin is used to find leakage in water network using sensor data as input.
                              -------------------
        begin                : 2017-02-06
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Nancy_Kapri
        email                : nancypesit@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import *  #we need QMenu for adding multiple menu's so need QMenu from PyQt4
from qgis.PyQt.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from leak_detection_dialog import LeakDetectionDialog
from find_error_dialog import FindErrorDialog
import os.path
from qgis.core import QgsMapLayerRegistry
from qgis.core import QgsMapLayer
from qgis.core import QgsField
from qgis.core import QgsExpression


data_dict = {} #outflow
data_dict_inflow = {} #inflow
adjacency_dict={}
path_loop=[]
loop_dict={}
flowrate={}
data_dict_inflow={}
deviation={}
direction={}
list_edges=set(frozenset())
big_loop=set(frozenset())
data_dict_sensor={}       #this dict stored the sensor data in this dictionary
pipe_dict={}
filename_line=""
filename_pt=""
layer_list_pt=[]
layer_list_line=[]
sensor_dict={}
class LeakDetection:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LeakDetection_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Leak_Detection')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LeakDetection')
        self.toolbar.setObjectName(u'LeakDetection')
        
        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LeakDetection', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        # self.dlg = LeakDetectionDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/LeakDetection/icon.png'
      			
        self.add_action(
            icon_path,
            text=self.tr(u'Equilibrium calculation'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.add_action(
		    icon_path,
			text=self.tr(u'Error calculation'),
			callback=self.run_error,
			parent=self.iface.mainWindow())			


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Leak_Detection'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    
    def select_output_file(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.txt')
        self.dlg.lineEdit.setText(filename)
    def select_file_point(self):
        filename_pt = QFileDialog.getSaveFileName(self.dlg, "Select pipe CSV or shape file ","", '*.shp')
        self.dlg.comboBox.addItem( filename_pt) 
        vlayer_pt=self.iface.addVectorLayer(filename_pt,"Point data","ogr")		
    def select_equilibrium_data(self):
        filename_equ = QFileDialog.getSaveFileName(self.dlg, "Select line CSV or shape file ","", '*.shp*')
        line_data="Equilibrium_Data"	
        layer_list_line = QgsMapLayerRegistry.instance().mapLayers().values()    
        #print " pehle now",layer_list_line		
        vlayer_line=self.iface.addVectorLayer(filename_equ,line_data,"ogr")	
        self.dlg.comboBox_2.addItem(line_data)   	
    def select_sensor_data(self):
        print "NO SENSOR"
        filename = QFileDialog.getSaveFileName(self.dlg, "Select sensor file ","", '*.txt')
        self.dlg.lineEdit.setText(filename)		
    def select_file_line(self):
        print ""	
        filename_line = QFileDialog.getSaveFileName(self.dlg, "Select line CSV or shape file ","", '*.shp*')
        line_data="Line_Data"	
        layer_list_line = QgsMapLayerRegistry.instance().mapLayers().values()    
        print " pehle now",layer_list_line		
        vlayer_line=self.iface.addVectorLayer(filename_line,line_data,"ogr")	
        self.dlg.comboBox_2.addItem(line_data) 	
        
        layer_list_line.append(vlayer_line)		
        print "layer list",layer_list_line	
        #print "add ho gyi"
    def select_canvas(self):
        if self.dlg.checkBox.isChecked():
            print "CHECKED"
			
        else:
            print "nothin checked"		
    def run_error(self):
        print "EROR"	
        #create the dialog
        self.dlg = FindErrorDialog()
        self.dlg.lineEdit.clear() 
        	
        self.dlg.toolButton.clicked.connect(self.select_sensor_data)
        self.dlg.toolButton_2.clicked.connect(self.select_equilibrium_data)	
        self.dlg.checkBox.stateChanged.connect(self.select_canvas) 		
        layer_list_line=[]		
        layer_list_line = QgsMapLayerRegistry.instance().mapLayers().values()
        print "layer now FOR ERROR ",layer_list_line		
        for layer in layer_list_line:
            if layer.type() == QgsMapLayer.VectorLayer:
                #print "laye name",layer.name()			
                self.dlg.comboBox.addItem( layer.name(), layer ) 			
        #show the dialog for form 2 wich is FindErrorDialog class    		
        self.dlg.show()		
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:                                                  
            filename = self.dlg.lineEdit.text()
            print "filename",filename			
            output_sensor_file = open(filename, "r")
            selectedLayerIndex = self.dlg.comboBox.currentIndex()  #this is needed for line data length,dia,fric so call the open_file function
            layer_list_line = QgsMapLayerRegistry.instance().mapLayers().values()			
            print "YO",selectedLayerIndex,layer_list_line
            	
            selectedLayer = layer_list_line[selectedLayerIndex]
            print " ERROR LAYER",selectedLayer
            fields = selectedLayer.pendingFields()
            fieldnames = [field.name() for field in fields]
            print "names",type(fieldnames[0])	
            
            			
			
            open_file_sensor(filename) 
            #print "dict for sensor",data_dict_sensor
            for feature in selectedLayer.getFeatures():
                node_1=feature["node1"]     				
                node_2=feature["node2"] 	
                flow_data=feature["flow rates"]
                #print "nodhfdv",node_1,node_2,flow_data,type(node_1)
                ls=[]		
                if int(node_1) in data_dict_sensor:
					ls=data_dict_sensor[int(node_1)]
					#print "lsss",ls,len(ls)
                for m in range(0,len(ls)):
                    lls=ls[m]
                    node2=lls[0] 	
                    flow_sensor=lls[1]					
                    
                    #print "node_1",node_1,node_2,node2,type(int(node_2)),type(node2),(int(node2)==int(node_2))						
                    if int(node2)==int(node_2):
                        if float(flow_data)==float(flow_sensor): 
                            print " NO ERROR "
						
                        else:
                            print "ERROR in FLOW",node2,node_2,flow_sensor,flow_data,type(flow_sensor),type(flow_data) 		
                            '''
							pay=QgsPalLayerSettings()
                            pay.readFromLayer(selectedLayer)
                            #print "layer",selectedLayer							
                            pay.enabled=True
                            pay.fieldName='flow rates'.encode('utf-8')           		
                            pay.placement=QgsPalLayerSettings.AroundPoint
                            pay.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'20','')
                            pay.writeToLayer(selectedLayer)
                            QgsMapLayerRegistry.instance().addMapLayers([selectedLayer]) 
                            '''	
                            selectedLayer.setCustomProperty("labelling","pal")
                            selectedLayer.setCustomProperty("labeling/enabled","true")
                            selectedLayer.setCustomProperty("labeling/fieldname","flow rates")
                            #selectedLayer.setCustomProperty("labeling/placement",QgsPalLayerSettings.Line)
                            selectedLayer.setCustomProperty("labeling/fontSize","8")
                            
                        selectedLayer.triggerRepaint() 							
                    				
    
    def run(self):
        """Run method that performs all the real work"""
        #create the dialog
        self.dlg = LeakDetectionDialog()		       
        self.dlg.comboBox.clear()
        self.dlg.comboBox_2.clear()
        #this is for pipe        
        layer_list_pt = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layer_list_pt:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.comboBox.addItem(layer.name(),layer)			
		#for junction        		
        layer_list_line = QgsMapLayerRegistry.instance().mapLayers().values()
        print "layer now",layer_list_line		
        for layer in layer_list_line:
            if layer.type() == QgsMapLayer.VectorLayer:
                #print "laye name",layer.name()			
                self.dlg.comboBox_2.addItem( layer.name(), layer ) 			

        
        self.dlg.lineEdit.clear()        
        self.dlg.pushButton.clicked.connect(self.select_output_file)		       
        self.dlg.toolButton.clicked.connect(self.select_file_point)
        print "layer list line sabse pehle",layer_list_line,type(layer_list_line)		        
        self.dlg.toolButton_2.clicked.connect(self.select_file_line)	
        # show the dialog		
        self.dlg.show()
		
        # Clear the QComboBox before loading layers
        		
        
        '''
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.comboBox.addItem( layer.name(), layer ) 
		
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.comboBox_2.addItem( layer.name(), layer ) 		
		
        '''
        
        
        
        #print "lay",lay		
		
		
		
		
		
		#this is for junction
        #layers = self.iface.legendInterface().layers()
        '''	
        layers = self.iface.activeLayer()
        print "layers for pipe",layers			
        for layer in layers:
            layer_list_line.append(layer.name())
        print "layer check",layer_list_line	
        self.dlg.comboBox_2.addItems(layer_list_line)  
        '''		
        
		
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
               
                        
            filename = self.dlg.lineEdit.text()
            output_file = open(filename, 'w')     			
            selectedLayerIndex = self.dlg.comboBox_2.currentIndex()  #this is needed for line data length,dia,fric so call the open_file function
            layer_list_line = QgsMapLayerRegistry.instance().mapLayers().values()			
            #print "YO",selectedLayerIndex,layer_list_line
            	
            selectedLayer = layer_list_line[selectedLayerIndex]
            print " laye rkaun hai",selectedLayer
            fields = selectedLayer.pendingFields()
            fieldnames = [field.name() for field in fields]
            print "names",fieldnames
           
            if "start_x" not in fieldnames:
                selectedLayer.dataProvider().addAttributes([QgsField("start_x",QVariant.Double)])
            if "end_x" not in fieldnames:
                selectedLayer.dataProvider().addAttributes([QgsField("end_x",QVariant.Double)]) 		
            if "start_y" not in fieldnames:
                selectedLayer.dataProvider().addAttributes([QgsField("start_y",QVariant.Double)])
            if "end_y" not in fieldnames:
                selectedLayer.dataProvider().addAttributes([QgsField("end_y",QVariant.Double)])	
		    #this is used to add new fiels i.e x_start,x_end,y_start,y_end from shape file to attribute table using regex
            #selectedLayer.dataProvider().addAttributes([QgsField("start_x",QVariant.Double),QgsField("end_x",QVariant.Double),QgsField("start_y",QVariant.Double),QgsField("end_y",QVariant.Double)])
            selectedLayer.updateFields()
            selectedLayer.startEditing()     
            
            idx1=selectedLayer.fieldNameIndex("start_x")
            e1=QgsExpression(""" $x_at(0) """)
            e1.prepare(selectedLayer.pendingFields())
			
            idx2=selectedLayer.fieldNameIndex("end_x")
            e2=QgsExpression(""" $x_at(-1) """)
            e2.prepare(selectedLayer.pendingFields())
			
            idy1=selectedLayer.fieldNameIndex("start_y")
            e3=QgsExpression(""" $y_at(0) """)
            e3.prepare(selectedLayer.pendingFields())
			
            idy2=selectedLayer.fieldNameIndex("end_y")
            e4=QgsExpression(""" $y_at(-1) """)
            e4.prepare(selectedLayer.pendingFields())
            
            for f in selectedLayer.getFeatures():
                f[idx1]=e1.evaluate(f)
                f[idx2]=e2.evaluate(f)
                f[idy1]=e3.evaluate(f)
                f[idy2]=e4.evaluate(f)
                selectedLayer.updateFeature(f)				
            selectedLayer.commitChanges()		
					
            #this is used to write teh attribute table to output file specified by user     				
            output_file.write(','.join(fieldnames)+ '\n') 			
            for f in selectedLayer.getFeatures():
                line = ','.join(unicode(f[x]) for x in fieldnames) + '\n'
                unicode_line = line.encode('utf-8')
                #print "line",unicode_line
                output_file.write(unicode_line)                                           
            output_file.close()
            #del output_file 			
            
           
            #this calls the main function which does all the flow rate calculations 
            open_file(filename)
            #add_to_table_flow(data_dict)			
            #index = self.dlg.layerCombo.currentIndex()
            #layer = self.dlg.layerCombo.itemData(index)
            #QMessageBox.information(self.iface.mainWindow(),"hello world","%s has %d features." %(layer.name(),layer.featureCount()))
            print "FIANLLL YY ",data_dict
           		
            #this is used to add flow rates from the dictionary to attribute table 		
            if "flow rates" not in fieldnames:			
                selectedLayer.dataProvider().addAttributes([QgsField("flow rates",QVariant.Double)])
            selectedLayer.updateFields()
            selectedLayer.startEditing()     
            
            #idx1=selectedLayer.fieldNameIndex("flow rates")   
            for feature in selectedLayer.getFeatures():
                node_1=feature["node1"]     				
                node_2=feature["node2"] 	
                #print "nodhfdv",node_1,node_2				
                #for i in data_dict:
                ls=data_dict[int(node_1)]
                for m in range(0,len(ls)):
                    lls=ls[m]
                    node2=lls[0] 	
                    flow=lls[4]					
                    
                    #print "node_1",node_1,node_2,node2,type(int(node_2)),type(node2),(int(node2)==int(node_2))						
                    if int(node2)==int(node_2): 
                        print "flow final for vector layer",flow						
                        feature["flow rates"]=flow	
                        selectedLayer.updateFeature(feature)						
            selectedLayer.commitChanges()					
            # Hello World program in Python
            '''
            selectedLayer.setCustomProperty("labeling/fieldname","flow rates")
            selectedLayer.setCustomProperty("labeling/placement",QgsPalLayerSettings.Line)
            selectedLayer.setCustomProperty("labeling/fontSize","8")
            selectedLayer.setCustomProperty("labeling/enabled","true")
            selectedLayer.triggerRepaint() 			
			'''
            '''
			label=QgsPalLayerSettings()
            label.readFromLayer(selectedLayer)
            label.enabled=True
            label.drawLabels=True			
            label.fieldName='$flow rates'
            			
            label.writetoLayer(selectedLayer)  			
            '''


	    
class Queue:
    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    #add first
    def add_first(self, item):
        self.items.insert(0,item)

    #delete last
    def dequeue_last(self):
        return self.items.pop()

    #delete first
    def dequeue_first(self):
        item=self.items
        self.items=[]
        for i in range(1,len(item)):
            self.items.insert(i-1,item[i])

    #add last
    def add_last(self,item):
        self.items.insert(self.size(),item)

    def size(self):
        return len(self.items)

    def peek(self):
        if not self.isEmpty():
            return self.items[0]

    def contains(self,item):
        for i in range(0,self.items.__sizeof__()):
            if self.items[i]==item:
                return True
            else:
                return False


    def display(self):
        for i in self.items:
            print (i)
        print ("over")

def open_file_sensor(path):
        print "path"
        f = open(path, "r")
        print path
        first_line=f.readline().strip()
        s=first_line.split(',')
   
        for i in range(0,len(s)):
            print s[i] 
            if s[i]=="node1":
                index_key=i
            if s[i]=="node2":
                index_node2=i                 	
            if s[i]=="flow rates":
                index_flow=i		
        #print index_key,index_node2,index_len,index_dia,index_fric	
        for i in iter(f):
            temp = i[:-1]
            temp = temp.split(',')
            key=int(temp[index_key])
            ls=[]
            ls.append(temp[index_node2])
       
            ls.append(temp[index_flow])
            print "kha error",key,ls
            if key in data_dict:
                lst2 = data_dict_sensor[key]
                lst2.append(ls)
            else:
                lst=[]
                lst.append(ls)
                data_dict_sensor[key] = lst 	
        #f.close()
        #del f		
def open_file(path):
    print "path"
    f = open(path, "r")
    print path
    first_line=f.readline().strip()
    s=first_line.split(',')
    #print s,len(s)	
    for i in range(1,len(s)):
        print s[i] 
        if s[i]=="node1":
            index_key=i
        if s[i]=="node2":
            index_node2=i
        if s[i]=="diamater":
            index_dia=i
        if s[i]=="length":
            index_len=i	
        if s[i]=="friction":
            index_fric=i		
    #print index_key,index_node2,index_len,index_dia,index_fric	
    for i in iter(f):
        temp = i[:-1]
        temp = temp.split(',')
        key=int(temp[index_key])
        ls=[]
        ls.append(temp[index_node2])
        ls.append(temp[index_len])
        ls.append(temp[index_dia])
        ls.append(temp[index_fric])
        #this is for outflow
        if key in data_dict:
            lst2 = data_dict[key]
            lst2.append(ls)
        else:
            lst=[]
            lst.append(ls)
            data_dict[key] = lst
        #this is for inflow
        if int(temp[index_node2]) in data_dict_inflow:
            lst=[]
            lst=data_dict_inflow[int(temp[index_node2])]
            lst.append(key)
        else:
            lst=[]
            lst.append(key)
            data_dict_inflow[int(temp[index_node2])]=lst
        #this is for adjacency list
        if key in adjacency_dict:
            lst3_adjcency=[]
            lst2_adjacency=adjacency_dict[key]
            lst2_adjacency.append(int(temp[index_node2]))
            y=int(temp[index_node2])
            if y in adjacency_dict:
                lst3_adjcency=adjacency_dict[int(temp[index_node2])]
                lst3_adjcency.append(key)
            else:
                lst3_adjcency.append(key)
                adjacency_dict[int(temp[index_node2])] = lst3_adjcency
        else:
            edgelist=[]
            lst3_adjcency=[]
            edgelist.append(int(temp[index_node2]))
            adjacency_dict[key]=edgelist
            x=int(temp[index_node2])
            if x in adjacency_dict:
                lst3_adjcency=adjacency_dict[int(temp[index_node2])]
                lst3_adjcency.append(key)
            else:
                lst3_adjcency.append(key)
                adjacency_dict[int(temp[index_node2])]=lst3_adjcency
    print ("outflow",data_dict)
    print ("adjacency",adjacency_dict)
    print ("inflow",data_dict_inflow)
    ##find the loops in the networkd now
    start=1
    #f.close()
    #del f	

    loop(start)    #found all the smaller loops  in network
    inflow=30
    source=1
    calculate_flowrate(source,inflow)
    calculate_k()
    #the direction is given
    direction[2]=[2,3,5,6,2]
    direction[3]=[3,4,5,3]
    calculate_correction()
    find_edges_of_loop()
    print data_dict
    corrected_flow() #this will now + or - from flowrate and deviation calculated
    print data_dict
    minor_loss()
    return data_dict
que_flow = Queue()
que_flow_trav = Queue()
holdinflow=Queue()

def minor_loss():
    print "nothing"

def find_edges_of_loop():

    for i in loop_dict:
        ld=loop_dict[i]
        for j in range(0,len(ld)-1):
            nod1=ld[j]
            nod2=ld[j+1]
            lst_edg=[nod1,nod2]
            list_edges.add(frozenset(lst_edg))
    print list_edges


def corrected_flow():
    for i in list_edges:
        #print i,type(i)
        el1,el2=i
        flow=0
        #print el1,el2
        node1=el1
        node2=el2
        dev=find_dev_for_correction(node1,node2)
        #print " node ",dev
        for m in dev:
            j=dev[m]
            #print j
            dev1=j
            add_sub_dev(node1,node2,dev1,m)

#this finally adds the dev to flowrate and updates the flowrate
def add_sub_dev(node1,node2,dev1,j):
    dire = find_direction(node1, node2,j)
    l1 = dire[0]
    l2 = dire[1]
    flag = dire[2]

    # print"recaqhd"
    nod2=[]
    if node1 in data_dict:
        nod2 = data_dict[node1]  # 4->[5...][7...]
        # we are searching 3 here
    for i in range(0, len(nod2)):
        m = nod2[i]  # [5..]
        nod = m[0]  # 5
        #print "ifpehle",l1,l2,type(l1)
        if int(nod) == node2 and l1 > l2 and flag == 1:  # if 3==5 same
            #print " 1 me ho ", node1, node2, flag, l1, l2,dev1,j
            m[4] = float(m[4])-dev1


        if int(nod) == node2 and l1 < l2 and flag == 1:
            #print " 2 me ho ", node1, node2, flag, l1, l2
            m[4] = float(m[4])+dev1


        if int(nod) == node2 and l1 > l2 and flag == 0:  # if 3==5 same
            #print " 3 me ho  ", node1, node2, flag, l1, l2
            m[4] = float(m[4])-dev1


        if int(nod) == node2 and l1 < l2 and flag == 0:
            #print " 4 me ho  ", node1, node2, flag, l1, l2,dev1,j
            m[4] = float(m[4])+dev1


        # reverse 3->4 calculate
        no1=[]
        if node2 in data_dict:
            no1 = data_dict[node2]
            #print "esle hoo", l1, l2, type(l1),flag,type(flag),no1
        for i in range(0, len(no1)):
            m = no1[i]
            nod = m[0]
            #print (node1, " else ho ", nod)
            if int(nod) == node1 and l1 > l2 and flag == 1:  # 3-[4..][5..] so 4 found
                #print " 5 me ho", node1, node2, flag, l1, l2
                m[4] = float(m[4])+dev1


            if int(nod) == node1 and l1 < l2 and flag == 1:  # 3-[4..][5..] so 4 found
                #print " 6 me ho ",node1,node2,flag,l1,l2
                m[4] = float(m[4])-dev1


            if int(nod) == node1 and l1 < l2 and flag == 0:  # 3-[4..][5..] so 4 foun
                #print " 7 me ho ", node1, node2, flag, l1, l2
                m[4] = float(m[4])-dev1


            if int(nod) == node1 and l1 > l2 and flag == 0:  # 3-[4..][5..] so 4 found
                #print " 8 me ho  ", node1, node2, flag, l1, l2
                m[4]= float(m[4])+dev1

def  find_dev_for_correction(node1,node2):
    #print "no "
    list_deviation={}
    for i in loop_dict:
        #print " devi ",i
        ls=loop_dict[i]
        if (node1 in ls) and (node2 in ls):
            list_deviation[i]=deviation[i]
    return list_deviation

def calculate_k():
   for i in data_dict:
        hol=data_dict[i]  # for 2 = [3..][6..]
        for i in range(0,len(hol)):
            nod=hol[i]   #   [3..]
            no=nod[0]
            leng=nod[1]
            dia=nod[2]
            friction=nod[3]
            k=(0.0252*float(friction)*float(leng))/(pow(float(dia),5))
            nod.append(k)

   print ("after friction",data_dict)

def calculate_flowrate(source,inflow):

    for i in data_dict:
        if i==source:
            node=data_dict[i]
            node1=[]
            node1=node[0]
            node2=node1[0]
            que_flow.add_last(node2)
            node1.append(inflow)
            findflowrate(node2)
            print ("after flowrate",data_dict)


#this calculates the summation deviation
def calculate_correction():
    no=[]
    for j in loop_dict:
        num = 0
        den = 0
        correction=0

        no=loop_dict[j]   #[4,3,5,4]

        for i in range(0,len(no)-1):
            #print "for ",i,i+1,no[i]
            node1=no[i]    #4
            node2=no[i+1]   #3
            #print (node1," ho ",node2)
            nod2 = []
            l1=0
            l2=0
            dire=[]
            #3->[3,4,5,3] 2->[2,3,5,6,2] given
            dire=find_direction(node1,node2,j)
            l1=dire[0]
            l2=dire[1]
            flag=dire[2]
            #print"recaqhd"
            if node1 in data_dict:
                nod2=data_dict[node1]  #4->[5...][7...]
            #we are searching 3 here
            for i in range(0,len(nod2)):
                m=nod2[i]  #[5..]
                nod=m[0]   #5
                #print "ifpehle",l1,l2,type(l1)
                if int(nod)==node2 and l1>l2 and flag==1:  #if 3==5 same
                    #print " 1 me ho ", node1, node2, flag, l1, l2
                    flow=float(m[4])
                    k=m[5]
                    num-=flow*flow*k
                    den+=flow*k
                if int(nod)==node2 and l1<l2 and flag==1:
                    #print " 2 me ho ", node1, node2, flag, l1, l2
                    flow = float(m[4])
                    k = m[5]
                    num += flow * flow * k
                    den += flow * k
                if int(nod)==node2 and l1>l2 and flag==0:  #if 3==5 same
                    #print " 3 me ho  ", node1, node2, flag, l1, l2
                    flow=float(m[4])
                    k=m[5]
                    num-=flow*flow*k
                    den+=flow*k
                if int(nod)==node2 and l1<l2 and flag==0:
                    #print " 4 me ho  ", node1, node2, flag, l1, l2
                    flow = float(m[4])
                    k = m[5]
                    num += flow * flow * k
                    den += flow * k
            #reverse 3->4 calculate
            no1=[]
            if node2 in data_dict:
                no1=data_dict[node2]
                #print "esle hoo", l1, l2, type(l1),flag,type(flag)
            for i in range(0,len(no1)):
                m=no1[i]
                nod=m[0]
                #print (node1, " else ho ", nod)
                if int(nod)==node1 and l1>l2 and flag==1:  #3-[4..][5..] so 4 found
                    #print " 5 me ho", node1, node2, flag, l1, l2
                    flow=float(m[4])
                    k=m[5]
                    num+=flow*flow*k
                    den+=flow*k
                if int(nod)==node1 and l1<l2 and flag==1:  #3-[4..][5..] so 4 found
                    #print " 6 me ho ",node1,node2,flag,l1,l2
                    flow=float(m[4])
                    k=m[5]
                    num-=flow*flow*k
                    den+=flow*k
                if int(nod) == node1 and l1 < l2 and flag == 0:  # 3-[4..][5..] so 4 foun
                    #print " 7 me ho ", node1, node2, flag, l1, l2
                    flow = float(m[4])
                    k = m[5]
                    num -= flow * flow * k
                    den += flow * k
                if int(nod) == node1 and l1 > l2 and flag == 0:  # 3-[4..][5..] so 4 found
                    #print " 8 me ho  ", node1, node2, flag, l1, l2
                    flow = float(m[4])
                    k = m[5]
                    num += flow * flow * k
                    den += flow * k
        correction=(num/(2*den))
        #print ("ANS ",num,den,correction)
        #print "i",j
        deviation[j]=correction
    print "dev",deviation

def find_direction(node1,node2,k):
    #print"direction",node1,node2,k
    for i in direction:
        ls=direction[i]
        #print " ok ",ls
        if k in ls:
            for j in range(0,len(ls)-1):
                m=ls[j]
                n=ls[j+1]
                #print "in",m,n,node1,node2
                if (m==node1 and n==node2):
                    #print "first"
                    return [j,j+1,0]
                if (m==node2 and n==node1): #last 1,0 is flag to indicate if index of node1>node =1 else 0
                    #print "second"
                    return [j+1,j,1]

def findflowrate(nod):
    #print ("findflowrate")
    if not que_flow.isEmpty():
        node=int(que_flow.peek())
    else:
        node=0
    outflownode=[]
    #print (" 1  ",node)
    if node in data_dict:
        outflownode=data_dict[node]
        siz=data_dict_inflow[node]
        #print ("2 if",outflownode)
        if len(siz)>1:
            inflowadd=[]
            inflowadd=data_dict_inflow[node]
            #print ("inflow",inflowadd)
            flownode=0
            flag=0
            ct=0
            #print (" if if ", node)

            for i in range(0,len(inflowadd)):
                flownode=inflowadd[i]
                #print type(que_flow_trav.items[0]), type(inflowadd[i]), que_flow_trav.items
                #print (" if if flownode", ct,flownode,len(inflowadd))
                if ((str(inflowadd[i]) in que_flow_trav.items) and (ct==len(inflowadd)-1)):
                    holdinflow.add_last(flownode)
                    #print (" fin 1")
                    flag=1
                elif ((str(inflowadd[i]) in que_flow_trav.items) and (ct< len(inflowadd))):
                    ct=ct+1;
                    holdinflow.add_last(flownode)
                    #print (" find 2 ")
                    continue
                else:
                    que_flow.dequeue_first()
                    #print (" finflow 3")
                    findflowrate(que_flow.peek())


            if flag==1:
                flo=0
                while not holdinflow.isEmpty():
                    hold=[]
                    h=holdinflow.dequeue_last()
                    hold=data_dict[h]
                    for i in range(0,len(hold)):
                        tmp=hold[i]
                        tmp1=tmp[0]
                        #print "zozo",type(tmp1),type(node)
                        if int(tmp1)==node:
                            flo=flo+tmp[4]
                            #print (" flo ", flo)
                flowratefordis(node,flo)
        else:
            if len(data_dict_inflow[node]) == 1:
                l=data_dict_inflow[node]
                l1=l[0]
                inflow=data_dict[l1]
                inflow1=inflow[0]
                inflowrate=inflow1[4]
                #print (" else ",inflowrate)
            flowratio=inflowrate/len(outflownode)
            k=[]
            for i in range(0,len(outflownode)):
                h=data_dict[node]
                h1=h[i]
                h1.append(flowratio)
                j=[]
                fd=data_dict[node]
                fd1=fd[i]
                fd2=fd1[0]
                j.append(fd2)
                j.append(flowratio)
                k.append(j)
                flowrate[node]=k
                if fd2 not in que_flow.items:
                    que_flow.add_last(fd2)
                else:
                    continue
            que_flow_trav.add_last(que_flow.peek())
            que_flow.dequeue_first()
            mod=0
            mod=que_flow.peek()
            #print ("KOO ",que_flow.items)
            #print ("KOO ",que_flow_trav.items)

            findflowrate(mod)
    else:
        que_flow_trav.add_first(que_flow.peek())
        que_flow.dequeue_first()
        if not que_flow.isEmpty():
            #print (" peek ",que_flow.peek())
            findflowrate(que_flow.peek())
        #print ("KOO else",que_flow.items)
        #print ("KOO else",que_flow_trav.items)

def flowratefordis(node,flow):
    #print "for this ",node,flow
    inflow1=flow
    outflownode=[]
    outflownode=data_dict[node]
    flowratio=inflow1/len(outflownode)
    k=[]
    for i in range(0,len(outflownode)):
        hg=data_dict[node]
        hf=hg[i]
        hf.append(flowratio)
        j=[]
        fd = data_dict[node]
        fd1 = fd[i]
        fd2 = fd1[0]
        j.append(fd2)
        j.append(flowratio)
        k.append(j)
        flowrate[node] = k
        if fd2 not in que_flow.items:
            que_flow.add_last(fd2)
        else:
            continue
        que_flow_trav.add_last(que_flow.peek())
        que_flow.dequeue_first()
        mod = 0
        mod = que_flow.peek()
        findflowrate(mod)

def loop(start):
    que= Queue()
    que_travel= Queue()
    que.add_last(start)
    que_travel.add_last(start)
    node=0
    while que.size()>0:
        node=que.peek()
        list_edges=[]
        if adjacency_dict.__contains__(node):
            list_edges=adjacency_dict[node]
        for i in range(0,len(list_edges)):
            temp=list_edges[i]
            if temp in que.items:
                path=[]
                temp_loop=[]
                temp_path_loop=bfs2(node,temp,path)

                min_size_loop=999999999
                min_index=0
                for i in range(0,len(temp_path_loop)):
                    if min_size_loop > len(temp_path_loop[i]):
                        min_size_loop=len(temp_path_loop[i])
                        min_index=i
                    else:
                        print "else",temp_path_loop[i]
                        big_loop.add(frozenset(temp_path_loop[i]))
                temp_loop=[]
                temp_loop=temp_path_loop[min_index]
                print "big",big_loop
                temp_loop.append(node)
                loop_dict[node]=temp_loop
                que.dequeue_last()
            #print (" conatins travel",temp,que_travel.items)
            if temp in  que_travel.items:
                continue
            else:
                que.add_last(temp)
        que.dequeue_first()
        que_travel.add_last(que.peek())
    print ("loop",loop_dict)

def bfs2(node,target,path):
    path.append(node)
    if(node==target):
        if(len(path)>2):
            path_loop.append(path)
    else:
        list_edges = []
        list_edges = adjacency_dict[node]
        for i in range(0,len(list_edges)):
            temp=list_edges[i]
            path_temp=[]
            if temp not in path:
                len_path=len(path)
                i=0
                while(len_path>0):
                    path_temp.append(path[i])
                    len_path=len_path-1
                    i=i+1
                bfs2(temp,target,path_temp)
    return path_loop


    
			