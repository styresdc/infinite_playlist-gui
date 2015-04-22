#!/usr/bin/env python
# -*- coding: CP1252 -*-
#
# generated by wxGlade 0.7.0 (standalone edition) on Tue Apr 21 17:41:02 2015
#
#   ######GUI IMPLEMENTATION####
#

import wx
import infinite_playlist as pl

# begin wxGlade: dependencies
import gettext
# end wxGlade

# begin wxGlade: extracode
# end wxGlade

filename = ""

class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        wx.Frame.__init__(self, *args, **kwds)
        self.title = wx.StaticText(self, wx.ID_ANY, _("Infinite_Playlist\n"))
        self.button_1 = wx.ToggleButton(self, wx.ID_ANY, _("Select Directory"))
        self.button_2 = wx.ToggleButton(self, wx.ID_ANY, _("Start"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_pushDir, self.button_1)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_pushPlay, self.button_2)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle(_("frame_1"))
        self.button_1.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DDKSHADOW))
        self.button_1.SetForegroundColour(wx.Colour(138, 247, 255))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.title, 0, wx.EXPAND, 0)
        sizer_1.Add(self.button_1, 0, 0, 0)
        sizer_1.Add(self.button_2, 0, 0, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

    def on_pushDir(self, event):  # wxGlade: MyFrame.<event_handler>
        dlg = wx.DirDialog(self, message="Choose a file")
 
        if dlg.ShowModal() == wx.ID_OK:
 
            # get the new filename from the dialog
            filename = dlg.GetPath()
        dlg.Destroy()  # best to do this sooner than later
 
        if filename:
            print filename

    def on_pushPlay(self, event):  # wxGlade: MyFrame.<event_handler>
        print "Starting"
	print filename
	pl.run(filename)
        event.Skip()

# end of class MyFrame
if __name__ == "__main__":
    gettext.install("inf_plist") # replace with the appropriate catalog name

    inf_plist = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frame_1 = MyFrame(None, wx.ID_ANY, "")
    inf_plist.SetTopWindow(frame_1)
    frame_1.Show()
    inf_plist.MainLoop()



###
###
###		### END GUI ###
###
