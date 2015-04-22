## IP-GUI

Implementing a GUI for rmparry infinire_playlist

**Problem**

infinite_plylist currently is not very user-friendly. Since we'd like to see it progress and be able to do more things, it would be nice to see it be able to interact with a user easily. 


**Process**

Wxglade uses wxPython to create simple guis that are designed and built in Python. This allows for seamless deployment across platfors with wxglade already setup. This gui simply contains radio buttons to complete it's tasks allowing for chnages within infinite_playlist.


**Dependencies**

To use aqplayer.py, you will need:

      - wx
      - all requirements for infinite_playlist

**Example**

Right now, we can select a directory and start up IP
```python
def on_pushDir(self, event):  # wxGlade: MyFrame.<event_handler>
        dlg = wx.DirDialog(self, message="Choose a file")
 
        if dlg.ShowModal() == wx.ID_OK:
 
            # get the new filename from the dialog
            filename = dlg.GetPath()
        dlg.Destroy()  # best to do this sooner than later
 
        if filename:
            print filename
```
```python
def on_pushPlay(self, event):  # wxGlade: MyFrame.<event_handler>
        print "Starting"
	print filename
	pl.run(filename)
        event.Skip()
```

**Code Explanation**

These two buttons control radio functions both within the GUI (direectory selection) and in IP (init) the design comes from central elements
```python
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
```
From here, we can begin to implement other changes as needed especially things like current song, pause, the map, and eventaully controls such as brach feasability.
