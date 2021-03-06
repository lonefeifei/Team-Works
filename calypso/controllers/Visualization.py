import logging

from pylons import request, response, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from calypso.lib.base import BaseController, render
from calypso import session as calypso_session
from calypso.model.meta import Session as sqlsession
from calypso.model.meta import metadata
log = logging.getLogger(__name__)

from calypso.tlm.windows import *
from calypso.tlm import Format
import calypso.tlm

class TileSelector(object):

    def __init__(self, type, title):
        self.text=title
        self.img=type+".png"
        self.id=type


class Palette_Menu(object):

    def __init__(self,title, selectors):
        self.title=title
        self.tileselectors=selectors
        self.expanded=False


    @staticmethod
    def create_menu():
        c.palette_menus=[]
        c.palette_menus.append(Palette_Menu(title='Snapshot',
                                      selectors=[TileSelector('gauge','Gauge'),
                                                 TileSelector('piechart','Pie Chart'),
                                                 TileSelector('table','Table'),
                                                 TileSelector('barchart','Bar Chart')]))
        c.palette_menus.append(Palette_Menu(title='Time Series',
                                      selectors=[TileSelector('linechart','Line Graph'),
                                                 TileSelector('areachart','Area Graph'),
                                                 TileSelector('columnchart', 'Column Graph')]))
        c.palette_menus.append(Palette_Menu(title='Intensity Maps',
                                           selectors=[TileSelector('heatmap','Intensity Map')]))
         

class DisplayModel:

    class DAO(object):
        table=None

        def __init__(self, name, format,user):
            self.name = name
            self.format = format
            self.user=user;
            sqlsession.add(self)            
            sqlsession.commit()
            
    def __init__(self, user, name, format):
        daos = sqlsession.query(DisplayModel.DAO).filter_by(user=user, name=name).all()
        if len(daos)>0:
            self.dao=daos[0]
        else:
            if format==None:
                self.dao = DisplayModel.DAO( name=name, format=Format.DEFAULT_FORMAT.get_name() , user = user)
            else:
                self.dao = DisplayModel.DAO( name=name, format=format , user=user)
                
    def get_name(self):
        try:
            return self.dao.name
        except:
            sqlsession.commit()
            sqlsession.add(self.dao)
            sqlsession.commit()
            return self.dao.name
        
    def get_format(self):
         return self.dao.format
        
    def set_name(self, name):
        self.dao.name = name
        sqlsession.add(self.dao)       
        sqlsession.commit()
        
    def delete(self):        
        sqlsession.delete(self.dao)
        sqlsession.commit()        

    def copy_to(self, newname):
        olddisplay=self
        oldname=self.dao.name
        if newname==oldname:
            return
        daos = sqlsession.query(DisplayModel.DAO).filter_by(user=self.dao.user, name=newname).all()
        if len(daos)>0:
            raise Exception("Name already exists")
        sqlsession.commit()
        format=self.dao.format
        user=self.dao.user
        self.dao=None
        self.dao=DisplayModel(user = user, name=newname, format=format).dao
        sqlsession.add(self.dao)
        sqlsession.commit()
        if (oldname=='unnamed'):
            olddisplay.delete()
  
    @staticmethod
    def get_model(user, displayname, format=None):
        return DisplayModel(user, displayname, format)
        
        

class VisualizationController(BaseController):

     
    def __init__(self):
        BaseController.__init__(self)
        self.isloaded=False
        c.configuration = request.params["configuration"]
        c.scenario      = request.params["scenario"]
        calypso.tlm.load(c.configuration)
        #self.user=session['user']
        self.format=None
        self.model=None
        
    def __before__(self,action):
        BaseController.__before__(self, action)
        if not(calypso_session.has_key(self.user)): calypso_session[self.user]={}
 
        if request.params.has_key("display"):
            displayname=request.params['display']
            self.model=DisplayModel.get_model(self.user, displayname)
        #elif calypso_session[self.user].has_key('display'):
        #    self.model=calypso_session[self.user]['display'].model
        else:
            self.model=DisplayModel.get_model(user=self.user, displayname="unnamed")
            self.format=Format.get_format("Default")
        if not(self.format):
            self.format=Format.get_format(self.model.get_format())
        c.display=self
        self.tabs = TelemetryWindow.get_tabs(self, self.user)
        self.tabstable={}
        if len(self.tabs)==0:
            self.add_new_tab()
        for tab in self.tabs:
            self.tabstable[tab.get_name()]=tab
        if not(calypso_session[self.user].has_key('display')) or calypso_session[self.user]['display']==None:            
            self.isloaded = True
            calypso_session[self.user]['display']=self
        #else:
        #    self.tabs=calypso_session[self.user]['display'].tabs
        #    self.tabstable=calypso_session[self.user]['display'].tabstable      
        if request.params.has_key('tab'):      
            c.selected = str(request.params["tab"])
        else:
            c.selected = self.tabstable.keys()[0]
        c.window=self.tabstable[c.selected]
        try:
            c.window=self.tabstable[c.selected]
        except:
            if len(self.tabs) == 0:
                self.add_new_tab()
                keys=self.tabstable.keys()
                c.selected = keys[0]
        c.tabs=self.tabs
        c.name=self.model.get_name()
        Palette_Menu.create_menu()
        c.selected_tile=None
        calypso_session[self.user]['display']=self
        if request.params.has_key('theme'):
            c.theme=request.params['theme']
         
    def load(self):
        if not(self.isloaded):
            self.isloaded = True
            calypso_session[self.user]['display']=self
            self.tabs = TelemetryWindow.get_tabs(self, self.user)
            self.tabstable={}
            for tab in self.tabs:
                self.tabstable[tab.get_name()]=tab
            c.tabs=self.tabs
            c.window=self.tabstable[c.selected]
       
        
    def get_name(self):
        return self.model.get_name()

    def get_short_name(self):
        return self.model.get_name().replace(self.user+'::','').replace('[','').replace(']','')
    
    def get_window(self,name):
        return self.tabstable[name]

    def edit(self):
        # Return a rendered template
        # return render('/Visualization.mako')
        # or, return a response
        return render('/tlm/develop/Visualization.html')
    
#    def tile_editor_placeholder(self):
#        #response.content_type='application/xhtml+xml'
#        return render('/tlm/develop/Visualization-editor_placeholder.html')

    def display(self):
        return render('/tlm/develop/Visualization-main.html');        
    
    def initialize(self):
        count=0
        target=len(c.all_monitors)
        for monitor in c.all_monitors:
            html='<script>if(!parent.monitors) parent.monitors={}; var attrs={};$=parent.$;'
            count+=1;
            for attr in monitor.attrs():
                html+= "attrs['"+ attr[0]+"']=true;";
            html=html + "$('#progressbar').progressbar({value:" + str(count*100/target) + "});"
            html+="parent.monitors['"+monitor.get_name()+"']={name: '"+monitor.get_name()+"', attrs:attrs};"
            if (count==target):
                html+="$('#progress_area').css('display','none');parent.calypso.tlm.tile_editor.monitor_available(parent.monitors);"
            html+="""
               
            </script>"""
            
            yield html;
    
    def append_tile(self):
        self.load()
        y_pos=int(request.params['y_pos'])
        x_pos=int(request.params['x_pos'])
        tiletype=request.params['type']
        c.selected=request.params['tab']
        c.window=self.tabstable[c.selected]
        index=0
        basename=c.window.get_name()+"_Tile"
        while c.window.has_tile(basename+str(index)):
            index+=1        
        tile=Tile(name=basename+str(index), user=self.user, parent=c.window, display=self, type=tiletype)
        properties=DisplayProperties(user=self.user, parent=tile, display=self, x_pos=x_pos, y_pos=y_pos, type=tiletype )
        #DisplayProperties.create_properties(name=tile.get_name(), user=self.user, parent=tile, display=self, x_pos=x_pos, y_pos=y_pos, type=tiletype)
        c.window.place_tile( tile = tile, properties = properties)
        return render('/tlm/develop/Visualization-main.html') #tile.render_html(properties, True)
   
    def remove_tile(self):
        self.load()
        y_pos=int(request.params['y_pos'])
        x_pos=int(request.params['x_pos'])
        c.window.remove_tile(x_pos=x_pos, y_pos=y_pos)
        return render('/tlm/develop/Visualization-main.html')
        
    def rename_tab(self):
        self.load()
        newname=request.params['name']
        if newname != c.window.get_name():
            self.tabstable[newname]=self.tabstable[c.window.get_name()]
            del self.tabstable[c.window.get_name()]
            c.window.set_name(newname)
            c.selected=newname
        return render('/tlm/develop/Visualization-main.html')

    def select_tab(self):
        c.selected=request.params['tab']
        c.window=self.tabstable[c.selected]
        return render('/tlm/develop/Visualization-main.html')


    def remove_tab(self):
        self.load()
        c.selected=request.params['tab']
        self.tabstable[c.selected].delete()
        for index in range(len(self.tabs)):
            tab=self.tabs[index]
            if tab.get_name()==c.selected:
                del self.tabs[index]
                break
        del self.tabstable[c.selected]
        c.selected=self.tabs[0].get_name()
        c.window=self.tabs[0]
        return render('/tlm/develop/Visualization-main.html')

            
    def add_new_tab(self):
        try:
            basename="Window"
            index=0
            while self.tabstable.has_key(basename+str(index)):
                index+=1
            self.tabs.append( TelemetryWindow(self.user, basename+str(index),self))
            self.tabstable[basename+str(index)]=self.tabs[len(self.tabs)-1]
            c.tabs=self.tabs
            c.selected=basename+str(index)
            c.window=self.tabstable[basename+str(index)]
            return render('/tlm/develop/Visualization-main.html')
        except:
            print "REQUEST PARAMS: " + str(request.params)
            import traceback
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            raise
        
    def render_tile_editor(self):
        try:
            self.load()
            c.x_pos=int(request.params['x_pos'])
            c.y_pos=int(request.params['y_pos'])
            c.tile=c.window.tiles[c.y_pos][c.x_pos].tile
            c.properties=c.window.tiles[c.y_pos][c.x_pos].properties
                 
            return render('/tlm/develop/Visualization-tile_editor.html')
        except:
            import traceback
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            pass
        
    def move_tile(self):
        self.load()
        from_x_pos=int(request.params['from_x_pos'])
        from_y_pos=int(request.params['from_y_pos'])
        to_x_pos=int(request.params['to_x_pos'])
        to_y_pos=int(request.params['to_y_pos'])
        c.window.move_tile(from_x_pos=from_x_pos, from_y_pos=from_y_pos, to_x_pos=to_x_pos, to_y_pos = to_y_pos)
        c.selected_tile=c.window.select_tile(x_pos=to_x_pos, y_pos=to_y_pos)
        return render('/tlm/develop/Visualization-main.html')

        
    def save(self):
        sqlsession.commit()
    
     
    def set_name(self):        
        try:
            self.load() 
            self.model.set_name(request.params['newname'])
            for tab in self.tabs:
                tab.set_display(self)
            c.name=self.model.get_name()
            self.save()
            return self.edit()
        except:
            import traceback
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            pass

    def delete(self):
        for tab in self.tabs:
            tab.delete()
        self.model.delete()
        del self.model


    def copy_to(self):
        try:
            self.load()
            newname=request.params['newname']
            for tab in self.tabs:
                tab.copy_to(newname)
            self.model.copy_to(newname)
            c.name=self.model.get_name()
            self.save()
            return "alert('Display sucessfully saved under"+newname+"');"
        except:
            import traceback
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            return "alert('Error in saving display.  Perhaps name already exists');"
            #raise

 

DisplayModel.DAO.table=sqlalchemy.Table("TlmDisplays", metadata,
                                        Column('user', String(40), primary_key=True),
                                        Column('name',String(80),  primary_key=True),
                                        Column('format',String(80)),
                                        useexisting=True)


"""map tables to database"""
sqlalchemy.orm.mapper(DisplayModel.DAO, DisplayModel.DAO.table)
