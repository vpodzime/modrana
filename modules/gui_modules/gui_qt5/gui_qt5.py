# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# A modRana Qt 5 QtQuick 2.0 GUI module
# * it inherits everything in the base GUI module
# * overrides default functions and handling
#----------------------------------------------------------------------------
# Copyright 2013, Martin Kolman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------------
from __future__ import with_statement
import os
import sys
import re
import traceback
import math

import pyotherside

try:
    from StringIO import StringIO # python 2
except ImportError:
    from io import StringIO # python 3
from pprint import pprint

# modRana imports
import math
from modules.gui_modules.base_gui_module import GUIModule
from datetime import datetime
import time
import threading

from core.fix import Fix
from core import signal
from core.backports import six
from core import constants
from core.threads import threadMgr

SEARCH_STATUS_PREFIX = "search:status:"
SEARCH_RESULT_PREFIX = "search:result:"

def newlines2brs(text):
    """ QML uses <br> instead of \n for linebreak """
    return re.sub('\n', '<br>', text)

def getModule(m, d, i):
    return QMLGUI(m, d, i)

def point2dict(point):
    """ Convert a Point instance to a dict

        :param Point point: a Point object instance
        :returns dict: a dict representation of the point
    """
    return {
        "name" : point.name,
        "description" : point.description,
        "latitude" : point.lat,
        "longitude" : point.lon,
        "elevation" : point.elevation
    }


class QMLGUI(GUIModule):
    """A Qt + QML GUI module"""

    def __init__(self, m, d, i):
        GUIModule.__init__(self, m, d, i)

        # some constants
        self.msLongPress = 400
        self.centeringDisableThreshold = 2048
        self.firstTimeSignal = signal.Signal()
        size = (800, 480) # initial window size

        # often used module shortcuts
        self._location = None
        self._mapLayers = None

        # register exit handler
        pyotherside.atexit(self._shutdown)

        # window state
        self._fullscreen = False

        # get screen resolution
        # TODO: implement this
        #screenWH = self.getScreenWH()
        #print(" @ screen size: %dx%d" % screenWH)
        #if self.highDPI:
        #    print(" @ high DPI")
        #else:
        #    print(" @ normal DPI")

        # NOTE: what about multi-display devices ? :)

        ## add image providers

        self._imageProviders = {
            "icon" : IconImageProvider(self),
            "tile" : TileImageProvider(self),
        }

        with open("data/tile_not_found.png", "rb") as f:
            self._tileNotFoundImage = f.read()

        ## register the actual callback, that
        ## will call the appropriate provider base on
        ## image id prefix
        pyotherside.set_image_provider(self._selectImageProviderCB)

        # initialize theming
        self._theme = Theme(self)

        ## make constants accessible
        #self.constants = self.getConstants()
        #rc.setContextProperty("C", self.constants)

        ## connect to the close event
        #self.window.closeEvent = self._qtWindowClosed
        ##self.window.show()

        self._notificationQueue = []

        # provides easy access to modRana modules from QML
        self.modules = Modules(self)

        # search functionality for the QML context
        self.search = Search(self)

    def firstTime(self):
        self._location = self.m.get('location', None)
        self._mapLayers = self.m.get('mapLayers', None)

        # trigger the first time signal
        self.firstTimeSignal()

    def _shutdown(self):
        """Called by PyOtherSide once the QML side is shutdown.
        """
        print("Qt5 GUI: shutting down")
        self.modrana.shutdown()


    def getIDString(self):
        return "Qt5"

    def needsLocalhostTileserver(self):
        """
        the QML GUI needs the localhost tileserver
        for efficient and responsive tile loading
        """
        return False

    def isFullscreen(self):
        return self._fullscreen

    def toggleFullscreen(self):
        # TODO: implement this
        pass

    def setFullscreen(self, value):
        pass

    def setCDDragThreshold(self, threshold):
        """set the threshold which needs to be reached to disable centering while dragging
        basically, larger threshold = longer drag is needed to disable centering
        default value = 2048
        """
        self.centeringDisableThreshold = threshold

    def hasNotificationSupport(self):
        return True

    def notify(self, text, msTimeout=5000, icon=""):
        """trigger a notification using the Qt Quick Components
        InfoBanner notification"""
        # TODO: implement this

        #    # QML uses <br> instead of \n for linebreak
        #    text = newlines2brs(text)
        #    print("QML GUI notify:\n message: %s, timeout: %d" % (text, msTimeout))
        #    if self.rootObject:
        #      self.rootObject.notify(text, msTimeout)
        #    else:
        #      self._notificationQueue.append((text, msTimeout, icon))
        return

    def openUrl(self, url):
        # TODO: implement this
        pass

    def _getTileserverPort(self):
        m = self.m.get("tileserver", None)
        if m:
            return m.getServerPort()
        else:
            return None

    def getScreenWH(self):
        # TODO: implement this
        pass

    def getModRanaVersion(self):
        """
        report current modRana version or None if version info is not available
        """
        version = self.modrana.paths.getVersionString()
        if version is None:
            return "unknown"
        else:
            return version

    def setPosition(self, posDict):
        lat, lon = float(posDict["latitude"]), float(posDict["longitude"])
        elevation = float(posDict["elevation"])
        metersPerSecSpeed = float(posDict["speedMPS"])  # m/s
        # report that we have 3D fix
        # (looks like we can't currently reliably discern between 2D
        # and 3D fix on the Jolla, might be good to check what other
        # Sailfish OS running devices report)
        self.set("fix", 3)

        self.set("pos", (lat, lon))

        # check if elevation is valid
        if not math.isnan(elevation):
            self.set("elevation", elevation)
        else:
            self.set("elevation", None)

        # check if speed is valid
        if not math.isnan(metersPerSecSpeed):
            self.set("speed", metersPerSecSpeed*3.6)
            self.set("metersPerSecSpeed", metersPerSecSpeed)
        else:
            self.set("speed", None)
            self.set("metersPerSecSpeed", None)

        # update done
        self.set('locationUpdated', time.time())
        # TODO: move part of this to the location module ?

    def _selectImageProviderCB(self, imageId, requestedSize):
        originalImageId = imageId
        providerId = ""
        #print("SELECT IMAGE PROVIDER")
        #print(imageId)
        #print(imageId.split("/", 1))
        try:
            # split out the provider id
            providerId, imageId = imageId.split("/", 1)
            # get the provider and call its getImage()
            return self._imageProviders[providerId].getImage(imageId, requestedSize)
        except ValueError:  # provider id missing or image ID overall wrong
            print("Qt5 GUI: provider ID missing: %s" % originalImageId)
        except AttributeError:  # missing provider (we are calling methods of None ;) )
            if providerId:
                print("Qt5 GUI: image provider for this ID is missing: %s" % providerId)
            else:
                import sys
                e = sys.exc_info()[1]
                print("Qt5 GUI: image provider broken, image id: %s" % originalImageId)
                print(e)
        except Exception:  # catch and report the rest
            import sys
            e = sys.exc_info()[1]
            print("Qt5 GUI: image loading failed, imageId: %s" % originalImageId)
            print(e)

    def _tileId2lzxy(self, tileId):
        """Convert tile id string to the "standard" lzxy tuple

        :param str tileId: map instance name/layer id/z/x/y

        :returns: lzxy tuple
        :rtype: tuple
        """
        split = tileId.split("/")
        # pinchMapId = split[0]
        layerId = split[1]
        z = int(split[2])
        x = int(split[3])
        y = int(split[4])
        # TODO: local id:layer cache ?
        layer = self.modules.mapLayers.getLayerById(layerId)
        return layer, z, x, y

    def addTileDownloadRequest(self, tileId):
        """Add an asynchronous download request, the tile will be
        notified once the download is finished or fails
        :param string tileId: unique tile id
        """
        try:
            lzxy = self._tileId2lzxy(tileId)
            self.modules._mapTiles.addTileDownloadRequest(lzxy, tileId)
        except Exception:
            import sys
            e = sys.exc_info()[1]
            print("Qt5 GUI: adding tile download request failed:")
            print(e)

class Modules(object):
    """A class that provides access to modRana modules from the QML context"""

    def __init__(self, gui):
        self._info = None
        self._stats = None
        self._mapLayers = None
        self._mapTiles = None
        self._storeTiles = None
        self.gui = gui

    @property
    def info(self):
        """A lazy evaluated property providing access to the info module"""
        if self._info is None:
            self._info = self.gui.m.get("info")
        return self._info
    
    @property
    def stats(self):
        """A lazy evaluated property providing access to the stats module"""
        if self._stats is None:
            self._stats = self.gui.m.get("stats")
        return self._stats

    @property
    def mapLayers(self):
        """A lazy evaluated property providing access to the stats module"""
        if self._mapLayers is None:
            self._mapLayers = self.gui.m.get("mapLayers")
        return self._mapLayers

    @property
    def mapTiles(self):
        """A lazy evaluated property providing access to the mapTiles module"""
        if self._mapTiles is None:
            self._mapTiles = self.gui.m.get("mapTiles")
        return self._mapTiles

    @property
    def storeTiles(self):
        """A lazy evaluated property providing access to the storeTiles module"""
        if self._storeTiles is None:
            self._storeTiles = self.gui.m.get("storeTiles")
        return self._storeTiles

class Search(object):
    """An easy to use search interface for the QML context"""

    def __init__(self, gui):
        self.gui = gui
        self._threadsInProgress = {}
        # register the thread status changed callback
        threadMgr.threadStatusChanged.connect(self._threadStatusCB)

    def search(self, searchId, query):
        """Trigger an asynchronous search (specified by search id)
        for the given term

        :param str query: search query
        """
        print("SEARCH!")
        print(searchId)
        print(query)
        online = self.gui.m.get("onlineServices", None)
        if online:
            # construct result handling callback
            callback = lambda x : self._searchCB(searchId, x)
            # get search function corresponding to the search id
            searchFunction = self._getSearchFunction(searchId)
            # start the search and remember the search thread id
            # so we can use it to track search progress
            # (there might be more searches in progress so we
            #  need to know the unique search thread id)
            print("SEARCH FUNCTION")
            print(searchFunction)
            threadId = searchFunction(query, callback)
            self._threadsInProgress[threadId] = searchId
            return threadId

    def _searchCB(self, searchId, results):
        """Handle address search results

        :param list results: address search results
        """
        # covert the Points in the results to a list of dicts
        resultList = []
        for result in results:
            resultList.append(point2dict(result))

        resultId = SEARCH_RESULT_PREFIX + searchId
        pyotherside.send(resultId, resultList)
        thisThread = threading.currentThread()
        # remove the finished thread from tracking
        if thisThread.name in self._threadsInProgress:
            del self._threadsInProgress[thisThread.name]

    def cancelSearch(self, threadId):
        """Cancel the given asynchronous search thread"""
        print("canceling search thread: %s" % threadId)
        threadMgr.cancel_thread(threadId)
        if threadId in self._threadsInProgress:
            del self._threadsInProgress[threadId]

    def _threadStatusCB(self, threadName, threadStatus):
        # check if the event corresponds to some of the
        # in-progress search threads
        recipient = self._threadsInProgress.get(threadName)
        if recipient:
            statusId = SEARCH_STATUS_PREFIX + recipient
            pyotherside.send(statusId, threadStatus)

    def _getSearchFunction(self, searchId):
        """Return the search function object for the given searchId"""
        online = self.gui.m.get("onlineServices", None)
        if online:
            if searchId == "address":
                return online.geocodeAsync
            elif searchId == "wikipedia":
                return online.wikipediaSearchAsync
            elif searchId == "local":
                return online.localSearchAsync
            else:
                print("Qt5 GUI: search function for id: %s not found" % searchId)
                return None
        else:
            print("Qt5 GUI: onlineServices module not found")


class ImageProvider(object):
    """PyOtherSide image provider base class"""
    def __init__(self, gui):
        self.gui = gui

    def getImage(self, imageId, requestedSize):
        pass


class IconImageProvider(ImageProvider):
    """the IconImageProvider class provides icon images to the QML layer as
    QML does not seem to handle .. in the url very well"""

    def __init__(self, gui):
        ImageProvider.__init__(self, gui)

    def getImage(self, imageId, requestedSize):
        #print("ICON!")
        #print(imageId)
        try:
            #TODO: theme name caching ?
            themeFolder = self.gui.modrana.paths.getThemesFolderPath()
            # fullIconPath = os.path.join(themeFolder, imageId)
            # the path is constructed like this in QML
            # so we can safely just split it like this
            splitPath = imageId.split("/")
            # remove any Ambiance specific garbage appended by Silica
            splitPath[-1] = splitPath[-1].rsplit("?")[0]
            fullIconPath = os.path.join(themeFolder, *splitPath)

            if not os.path.exists(fullIconPath):
                if splitPath[0] == constants.DEFAULT_THEME_ID:
                    # already on default theme and icon path does not exist
                    print("Icon not found in default theme:")
                    print(fullIconPath)
                    return None
                else:  # try to get the icon from default theme
                    splitPath[0] = constants.DEFAULT_THEME_ID
                    fullIconPath = os.path.join(themeFolder, *splitPath)
                    if not os.path.exists(fullIconPath):
                        # icon not found even in the default theme
                        print("Icon not found even in default theme:")
                        print(fullIconPath)
                        return None
            with open(fullIconPath, 'rb') as f:
                # the context manager will make sure the icon
                # file is properly closed
                return bytearray(f.read()), (-1,-1), pyotherside.format_data
        except Exception:
            import sys
            e = sys.exc_info()[1]
            print("Qt5 GUI: icon image provider: loading icon failed")
            print(e)
            print(os.path.join('themes', imageId))
            print("Traceback:")
            traceback.print_exc(file=sys.stdout) # find what went wrong


class TileImageProvider(ImageProvider):
    """
    the TileImageProvider class provides images images to the QML map element
    """

    def __init__(self, gui):
        ImageProvider.__init__(self, gui)
        self.gui = gui

        self.gui.firstTimeSignal.connect(self._firstTimeCB)

    def _firstTimeCB(self):
        # connect to the tile downloaded callback so that we can notify
        # the QML context that a tile has ben downloaded and should be
        # shown on the screen
        # NOTE: we need to wait for the firstTime signal as at GUI module init
        # the other modules (other than the device module) are not yet initialized
        self.gui.modules.mapTiles.tileDownloaded.connect(self._tileDownloadedCB)

    def _tileDownloadedCB(self, error, lzxy, tag):
        """Notify the QML context that a tile has been downloaded"""
        pinchMapId = tag.split("/")[0]
        #print("SENDING: %s %s" % ("tileDownloaded:%s" % pinchMapId, tag))
        pyotherside.send("tileDownloaded:%s" % pinchMapId, tag, error)

    def getImage(self, imageId, requestedSize):
        """
        the tile info should look like this:
        layerID/zl/x/y
        """
        #print("TILE REQUESTED %s" % imageId)
        #print(requestedSize)
        try:
            # split the string provided by QML
            split = imageId.split("/")
            pinchMapId = split[0]
            layerId = split[1]
            z = int(split[2])
            x = int(split[3])
            y = int(split[4])

            # TODO: local id:layer cache ?
            layer = self.gui.modules.mapLayers.getLayerById(layerId)

            # construct the tag
            #tag = (pinchMapId, layerId, z, x, y)
            #tag = (pinchMapId, layerId, z, x, y)

            # get the tile from the tile module
            tileData = self.gui.modules.mapTiles.getTile((layer, z, x, y),
                                                         async=True, tag=imageId,
                                                         download=False)
            imageSize = (256,256)
            if tileData is None:
                # The tile was not found locally
                # * in persistent storage (files/sqlite db)
                # * in the tile cache in memory
                # An asynchronous tile download request has been added
                # automatically, so we just now need to notify the
                # QtQuick GUI that it should wait fo the download
                # completed signal.
                #
                # We notify the GUI by returning a 1x1 image.
                tileData = self.gui._tileNotFoundImage
                imageSize = (1,1)
                #print("%s NOT FOUND" % imageId)
                # TODO: use some raw image data instead of PNG ?
            #print("RETURNING STUFF %d %s" % (imageSize[0], imageId))
            return bytearray(tileData), imageSize, pyotherside.format_data
        except Exception:
            import sys
            e = sys.exc_info()[1]
            print("Qt 5 GUI: tile image provider: loading tile failed")
            print(e)
            print(imageId)
            print(requestedSize)
            traceback.print_exc(file=sys.stdout)


class MapTiles(object):
    def __init__(self, gui):
        self.gui = gui

    @property
    def tileserverPort(self):
        port = self.gui._getTileserverPort()
        if port:
            return port
        else: # None,0 == 0 in QML
            return 0

    def loadTile(self, layerId, z, x, y):
        """
        load a given tile from storage and/or from the network
        True - tile already in storage or in memory
        False - tile download in progress, retry in a while
        """
        #    print(layerId, z, x, y)
        if self.gui._mapTiles.tileInMemory(layerId, z, x, y):
        #      print("available in memory")
            return True
        elif self.gui._mapTiles.tileInStorage(layerId, z, x, y):
        #      print("available in storage")
            return True
        else: # not in memory or storage
            # add a tile download request
            self.gui._mapTiles.addTileDownloadRequest(layerId, z, x, y)
            #      print("downloading, try later")
            return False

class _Search(object):
    _addressSignal = signal.Signal()

    changed = signal.Signal()

    test = signal.Signal()

    def __init__(self, gui):
        self.gui = gui
        self._addressSearchResults = None
        self._addressSearchStatus = "Searching..."
        self._addressSearchInProgress = False
        self._addressSearchThreadName = None
        self._localSearchResults = None
        self._wikipediaSearchResults = None
        self._routeSearchResults = None
        self._POIDBSearchResults = None
        # why are wee keeping our own dictionary of wrapped
        # objects and not just returning a newly wrapped object on demand ?
        # -> because PySide (1.1.1) segfaults if we don't hold any reference
        # on the object returned :)

        # register the thread status changed callback
        threadMgr.threadStatusChanged.connect(self._threadStatusCB)

    def _threadStatusCB(self, threadName, threadStatus):
        if threadName == self._addressSearchThreadName:
            self._addressSearchStatus = threadStatus
            self._addressSignal()

    def address(self, address):
        """Trigger an asynchronous address search for the given term

        :param address: address search query
        :type address: str
        """
        online = self.gui.m.get("onlineServices", None)
        if online:
            self._addressSearchThreadName = online.geocodeAsync(
                address, self._addressSearchCB
            )
        self._addressSearchInProgress = True
        self._addressSignal()

    def addressCancel(self):
        """Cancel the asynchronous address search"""
        threadMgr.cancel_thread(self._addressSearchThreadName)
        self._addressSearchInProgress = False
        self._addressSearchStatus = "Searching..."
        self._addressSignal()



    def _addressSearchCB(self, results):
        """Replace old address search results (if any) with
        new (wrapped) results

        :param results: address search results
        :type results: list
        """
        #self.gui._addressSearchListModel.set_objects(
        #    wrapList(results, wrappers.PointWrapper)
        #)

        self._addressSearchInProgress = False
        self._addressSignal.emit()

    #addressStatus = QtCore.Property(six.text_type,
    #    lambda x: x._addressSearchStatus, notify=_addressSignal)
    #
    #addressInProgress = QtCore.Property(bool,
    #    lambda x: x._addressSearchInProgress, notify=_addressSignal)

class ModRana(object):
    """
    core modRana functionality
    """

    def __init__(self, modrana, gui):
        self.modrana = modrana
        self.gui = gui
        self.modrana.watch("mode", self._modeChangedCB)
        self.modrana.watch("theme", self._themeChangedCB)
        self._theme = Theme(gui)
    # mode

    def _getMode(self):
        return self.modrana.get('mode', "car")

    def _setMode(self, mode):
        self.modrana.set('mode', mode)

    modeChanged = signal.Signal()

    def _modeChangedCB(self, *args):
        """notify when the mode key changes in options"""
        self.modeChanged()

class Theme(object):
    """modRana theme handling"""
    def __init__(self, gui):
        self.gui = gui
        # connect to the first time signal
        self.gui.firstTimeSignal.connect(self._firstTimeCB)
        self.themeModule = None
        self._themeDict = {}
        self.colors = None
        self.modrana = self.gui.modrana
        self.themeChanged.connect(self._notifyQMLCB)

    themeChanged = signal.Signal()

    def _firstTimeCB(self):
        # we need the theme module
        self.themeModule = self.gui.m.get('theme')
        theme = self.themeModule.theme
        # reload the theme dict so that
        # the dict is up to date and
        # then trigger the changed signal
        # and give it the current theme dict
        self.themeChanged(self._reloadTheme(theme))
        # connect to the core theme-modules theme-changed signal
        self.themeModule.themeChanged.connect(self._themeChangedCB)

    def _themeChangedCB(self, newTheme):
        """ Callback from the core theme module
        - reload theme and trigger our own themeChanged signal

        :param newTheme: new theme from the core theme module
        :type newTheme: Theme
        """
        self.themeChanged(self._reloadTheme(newTheme))

    def _notifyQMLCB(self, newTheme):
        """ Notify the QML context that the modRana theme changed

        :param newTheme: the new theme
        :type newTheme: dict
        """
        pyotherside.send("themeChanged", newTheme)

    @property
    def themeId(self):
        return self._themeDict.get("id")

    @themeId.setter
    def themeId(self, themeId):
        self.modrana.set('theme', themeId)

    @property
    def theme(self):
        return self._themeDict

    def _reloadTheme(self, theme):
        """Recreate the theme dict from the new theme object

        :param theme: new modRana Theme object instance
        :type theme: Theme
        """
        themeDict = {
            "id" : theme.id,
            "name" : theme.name,
            "color" : {
                "main_fill" : theme.getColor("main_fill", "#92aaf3"),
                "icon_grid_toggled" : theme.getColor("icon_grid_toggled", "#c6d1f3"),
                "icon_button_normal" : theme.getColor("icon_button_normal", "#c6d1f3"),
                "icon_button_toggled" : theme.getColor("icon_button_toggled", "#3c60fa"),
                "icon_button_text" : theme.getColor("icon_button_text", "black"),
                "page_background" : theme.getColor("page_background", "black"),
                "page_header_text" : theme.getColor("page_header_text", "black"),
            }
        }
        self._themeDict = themeDict
        return themeDict