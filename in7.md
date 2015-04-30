## IP-GUI / Inquiry Report 7

Implementing a GUI for rmparry infinite_playlist

**Problem**

infinite_plylist currently is not very user-friendly. Since we'd like to see it progress and be able to do more things, it would be nice to see it be able to interact with a user easily. 


**Process**

Wxglade uses wxPython to create simple guis that are designed and built in Python. This allows for seamless deployment across platfors with wxglade already setup. This gui simply contains radio buttons to complete it's tasks allowing for chnages within infinite_playlist.


**Status**

Our IP-GUI has been setup to allow for basic program manipulation currently. Such as selecting a directory and running our program. Currently i've been working addidn additional functionality to our GUI so that it may provide more control and information to our user.

**Problem**

IP-GUI now is currently rather basic, i'd like to see it's functionlatiy increased. We can start by;

1) Adding control elements to the GUI
2) Adding information to the GUI

**Implementation**

1)
  WxGlade will allow for additions to our current GUI, modfications to be made include adding pause functionality and stop functionality. Also, the user will be given an option to clear runtime files as thwy tend to take up a good amount of space. Since we are using function callbacks our IP.py does not currently allow for this so i've modified it to temporarily not clean at it's termination at cost of disk space. In the future, this will also be implemented when the user quits the program using a specifed button. 

  ```python
def on_pushQuit(self, event):  # wxGlade: MyFrame.<event_handler>
        print "Program Termination, cleaning up."
	pl.cleanup()
	sys.exit()
        event.Skip()
```

2)
  Adding information might prove to be a difficult task, threading may be an issue as IP uses one thread and continues automatically currrently. Strategic position of update function calls will need to take place as i'm not sure if IP can run in conccurence with the GUI in regards to communication while already performing tasks (playing). Thus, my current plan is to allow for strategic placement of code to update the GUI so that calls may be timed and not wasted. For example, where we currently print that a branch was taken, we can update a GUI counter element for number of branches taken. The same approach can be taken with updating things, such as the current beat and switching between songs. This will also be intersing for playback controls in the sense that there is no optuimum place a check to see if the user wishes to pause playback or quit. 
  
Eventually these new calls from the Gui will be handled in IP throgh the use of simple helper methods. 

**Where to go from here**

I'll be looking into strategic placement and assesing the Gui in multi threaded context. 

**Continued ip-gui docs**

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
