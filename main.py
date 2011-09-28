#!/usr/bin/env python

import sys
import re
import xml.dom.minidom
import uuid
import urllib
import os, os.path
import zipfile
import tempfile
import shutil
from lib import xmlpp



import pygtk
if not sys.platform == 'win32':
    pygtk.require("2.0")


import gtk
import gtk.glade


class mainWindow():
    """This is the Main Window Loader and bootstrap"""
    def __init__(self):
        self.TARGET_TYPE_URI_LIST = 80
        self.dnd_list = [ ( 'text/uri-list', 0, self.TARGET_TYPE_URI_LIST ) ]
        self.savedState = 0
        self.wTree = gtk.glade.XML("gui/main.glade")
        self.mainWindow = self.wTree.get_widget("windowMain")
        self.togglebutton =  self.wTree.get_widget("togglebuttonOPF")
        self.wTree.signal_autoconnect({"on_windowMain_destroy": self.killWindow,
                                       'on_windowMain_drag_data_received': self.on_drag_data_received,
                                       'on_togglebuttonOPF_toggled' : self.toggle_saved_state})
        self.mainWindow.drag_dest_set( gtk.DEST_DEFAULT_MOTION |
                  gtk.DEST_DEFAULT_HIGHLIGHT | gtk.DEST_DEFAULT_DROP,
                  self.dnd_list, gtk.gdk.ACTION_COPY)
        
    def toggle_saved_state (self, response):
        if self.savedState == 0:
            button_img =  self.wTree.get_widget("imageToggleButton")
            button_txt =  self.wTree.get_widget("labelToggleButton")
            button_img.set_from_stock('gtk-refresh', gtk.ICON_SIZE_BUTTON)
            button_txt.set_text("Restore Original OPF Data")
            self.savedState = 1
        else:
            button_img =  self.wTree.get_widget("imageToggleButton")
            button_txt =  self.wTree.get_widget("labelToggleButton")
            button_img.set_from_stock('gtk-apply', gtk.ICON_SIZE_BUTTON)
            button_txt.set_text("Save Current OPF Data and Create New UUID")
            self.savedState = 0
        
    def get_file_path_from_dnd_dropped_uri(self, uri):
        # get the path to file
        path = ""
        if uri.startswith('file:\\\\\\'): # windows
            path = uri[8:] # 8 is len('file:///')
        elif uri.startswith('file://'): # nautilus, rox
            path = uri[7:] # 7 is len('file://')
        elif uri.startswith('file:'): # xffm
            path = uri[5:] # 5 is len('file:')
    
        path = urllib.url2pathname(path) # escape special chars
        path = path.strip('\r\n\x00') # remove \r\n and NULL
    
        return path
    
    def on_drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        if target_type == self.TARGET_TYPE_URI_LIST:
            uri = selection.data.strip('\r\n\x00')
            uri_splitted = uri.split() # we may have more than one file dropped
            for uri in uri_splitted:
                path = self.get_file_path_from_dnd_dropped_uri(uri)
                if os.path.isfile(path):
                    original_epub = zipfile.ZipFile(path,"r")
                    original_opf = self.locate_opf_file(original_epub)
                    original_opf_data = original_epub.read(original_opf)
                    new_opf = xml.dom.minidom.parseString(original_opf_data)  
                    new_opf = self.swap_identifiers(new_opf)
                    new_epub_temp = tempfile.NamedTemporaryFile(delete=False)
                    new_epub = zipfile.ZipFile(new_epub_temp,"w")
                    uglyXml = new_opf.toxml()
                    prettyXml = xmlpp.get_pprint(uglyXml)
                    prettyXml = re.sub(r'>[\s]*([^<\s])', r'>\1', prettyXml)
                    prettyXml = re.sub(r'([^>\s])[\s]*<', r'\1<', prettyXml)
                    for item in original_epub.infolist():
                        if item.filename == "mimetype":
                            item_file_contents = original_epub.read(item.filename)
                            new_epub.writestr(item, item_file_contents, zipfile.ZIP_STORED)
                        elif not item.filename == original_opf:
                            item_file_contents = original_epub.read(item.filename)
                            new_epub.writestr(item, item_file_contents)
                        else:
                            new_epub.writestr(original_opf, prettyXml)
                    original_epub.close()
                    new_epub.close()
                    new_epub_temp.close()
                    shutil.copy(new_epub_temp.name, path)
                    os.unlink(new_epub_temp.name)
                    
                    
                else:
                    original_epub = None
                    
    
            
    def locate_opf_file(self, original_epub):
        opf_filename = None
        for filename in original_epub.namelist():
            if re.search("\.opf", filename, re.IGNORECASE):
                opf_filename = filename
        return (opf_filename)
    
    def swap_identifiers(self, opf):
        elements_to_add = []
        elements_to_remove = []
        elements_to_comment = []
        found_original = 0
        if opf.documentElement.hasAttribute("unique-identifier"):
            unique_ident_id = opf.documentElement.getAttribute("unique-identifier")
        else:
            opf.documentElement.setAttribute("unique-identifier", "BookID")
            unique_ident_id = "BookID"
        if not opf.getElementsByTagName('metadata')[0].hasAttribute("xmlns:opf"):
            opf.getElementsByTagName('metadata')[0].setAttribute("xmlns:opf", "http://www.idpf.org/2007/opf")
        if not opf.getElementsByTagName('metadata')[0].hasAttribute("xmlns:dc"):
            opf.getElementsByTagName('metadata')[0].setAttribute("xmlns:dc", "http://purl.org/dc/elements/1.1/")
        if self.savedState == 1:
            for meta_child in opf.getElementsByTagName('metadata')[0].childNodes:
                if meta_child.nodeType == 8:
                    in_comment = meta_child.nodeValue
                    in_comment = re.search('SJREHASHERDATA: \{ID: ([^,]*?), SCHEME: ([^,]*?), UID: ([^\}]*?)\}', in_comment, re.IGNORECASE)
                    if not in_comment == None:
                        found_original = 1
                        proto_xml = opf.createElement("dc:identifier")
                        if not in_comment.group(1) == '':
                            proto_xml.setAttribute("id", in_comment.group(1))
                        if not in_comment.group(2) == '':
                            proto_xml.setAttribute("opf:scheme", in_comment.group(2))
                        if not in_comment.group(3) == '':
                            proto_xml_uid = opf.createTextNode(in_comment.group(3))
                            proto_xml.appendChild(proto_xml_uid)
                        elements_to_add.append(proto_xml)
                        elements_to_remove.append(meta_child)
                        proto_xml = None
            for meta_child in opf.getElementsByTagName('metadata')[0].childNodes:
                if meta_child.nodeType == 1 and meta_child.tagName == "dc:identifier" and found_original == 1:
                    elements_to_remove.append(meta_child)
        if self.savedState == 0:
            new_uuid = opf.createElement('dc:identifier')
            new_uuid.setAttribute("opf:scheme", "UUID")
            new_uuid.setAttribute("id", unique_ident_id)
            new_uuid_value = opf.createTextNode("urn:uuid:"+str(uuid.uuid4()))
            new_uuid.appendChild(new_uuid_value)
            elements_to_add.append(new_uuid)
            for meta_child in opf.getElementsByTagName('metadata')[0].childNodes:
                if meta_child.nodeType == 8:
                    in_comment = meta_child.nodeValue
                    in_comment = re.search('SJREHASHERDATA: \{ID: ([^,]*?), SCHEME: ([^,]*?), UID: ([^\}]*?)\}', in_comment, re.IGNORECASE)
                    if not in_comment == None:
                        found_original = 1
            for meta_child in opf.getElementsByTagName('metadata')[0].childNodes:
                if meta_child.nodeType == 1 and meta_child.tagName == "dc:identifier" and found_original == 0:
                    elements_to_comment.append(meta_child)
                elif meta_child.nodeType == 1 and meta_child.tagName == "dc:identifier" and found_original == 1:
                    elements_to_remove.append(meta_child)
                    
        if found_original == 0:
            for comment_node in elements_to_comment:
                elements_to_remove.append(comment_node)
                elements_to_add.append(opf.createComment("SJREHASHERDATA: {ID: "+str(comment_node.getAttribute("id")).strip()+", SCHEME: "+str(comment_node.getAttribute("opf:scheme")).strip()+", UID: "+str(comment_node.firstChild.nodeValue).strip()+"}"))
        
        for remove_node in elements_to_remove:
            opf.getElementsByTagName('metadata')[0].removeChild(remove_node)
        for add_node in elements_to_add:
            opf.getElementsByTagName('metadata')[0].appendChild(add_node)
        
        return opf
        
                            
    def get_dc_identifier(self, opf):
        for ident in opf.getElementsByTagName("dc:identifier"):
            if ident.hasAttribute("id"):
                if ident.getAttribute("id").lower() == "bookid".lower():
                    return ident
    
    def killWindow (self, widget):
        print "killing! DIE DIE DIE STUPID PYTHON"
        sys.exit(0)
            

if __name__ == "__main__":
    rehasheriszer = mainWindow()
    gtk.main()
