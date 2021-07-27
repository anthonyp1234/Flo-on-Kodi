import sys, xbmcgui, xbmcplugin, xbmcaddon
import os, requests, re, json
from urllib.parse import urlencode, quote_plus, parse_qsl, quote, unquote

import pickle
import random
#import time

addon           = xbmcaddon.Addon(id='plugin.video.flo')
addon_url       = sys.argv[0]
addon_handle    = int(sys.argv[1])
addon_icon      = addon.getAddonInfo('icon')
addon_BASE_PATH = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

TOKEN_FILE = xbmc.translatePath(os.path.join('special://temp','flo_token_data.txt'))

PICTURE_FILES =  os.path.join(addon.getAddonInfo('path'),"resources", "pictures") #.decode('utf-8') ,"resources", "pictures")

DASH = False  ### If true use dash, otherwise use hls

#MONTH = 2678400 ##How much to remove to go back a month in unix time


urls = {
        "website_base" : "https://www.flograppling.com",
        "home" : "https://api.flograppling.com/api/experiences/web/home?version=1.2.3&limit=20&offset=0&site_id=8",
        "login_address" : "https://api.flograppling.com/api/tokens"
        
        }

headers = {
          "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
          "accept": "application/json, text/plain, */*",
          "sec-fetch-mode": "cors",
          "accept-encoding": "gzip, deflate, br",
          "accept-language": "en-AU,en;q=0.9",
          "content-type": "application/json",
          "sec-fetch-dest": "empty",
          "sec-fetch-site": "same-site",
          "authority": "api.flograppling.com"
         }

play_live_header = {
    'accept': '*/*',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9',
    'dnt': '1',
    'origin': 'https://www.flograppling.com',
    'referer': 'https://www.flograppling.com/',
    #'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
    'sec-ch-ua-mobile': '?0',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'
    }


def get_creds():
    """Get username and password. Return dict of username and password"""

    if len(addon.getSetting('username')) == 0 or len(addon.getSetting('password')) == 0:
        return None

    return {
        'email': addon.getSetting('username'),  
        'password': addon.getSetting('password')
    }

def get_auth_token():
    """Take in the credentials as dict['email', 'password'] and return the Auth token as string with the bearer keyword ready to be used in the header"""
    
    credentials = json.dumps(get_creds())

    session = requests.Session()
    #session.headers = headers
    response = session.post(urls["login_address"], headers=headers, data=credentials)
    session.close()
    info_dict = response.json()
    if response.status_code == 200:
        #token  = {"jwt_token" :info_dict["token"], "jwt_refresh_token": info_dict["refresh_token_exp"], "ajs_user_id" :info_dict["user"]["id"]}
        token = {"jwt_token" :info_dict["token"]}
        return token
        
    else:

        xbmc.log("Could not get Auth Token, Session text: {0}".format(str(session.json())),level=xbmc.LOGERROR)
        return False


def get_token():
    """Get the token either from the file saved or by getting a new one if the file doesn't exist"""
    
    xbmc.log("pickle path is is: {0}".format(str(TOKEN_FILE)),level=xbmc.LOGERROR)
    
    if not os.path.isfile(TOKEN_FILE): #if bearer token file does not exist
        token = get_auth_token()
        
        with open(TOKEN_FILE, 'wb') as handle:
            pickle.dump(token, handle, protocol=pickle.HIGHEST_PROTOCOL)
            ## Replace by above pickle.dump(open(TOKEN_FILE, mode='wb'))  ###THIS was added new, not sure why this wasn't here before?
        
    else:
        with open(TOKEN_FILE, 'rb') as handle:
            token = pickle.load(handle)
    
        ## replaced by above token = pickle.load(open(TOKEN_FILE), mode='rb')

    return token



def get_web_data(url, put_data=None, bearer_in_header=False):
    """Grab the web data from the url"""
    my_token = get_token()
    
    xbmc.log("116;URL Get req {0}\r\n".format(str(url)),level=xbmc.LOGERROR)
    
    session = requests.Session()
    
    if bearer_in_header==True:
        add_headers = headers
        my_auth = "Bearer " + my_token['jwt_token']
        add_headers['authorization'] = my_auth       
    else:
        add_headers = headers
    
    
    if not put_data and not bearer_in_header:
        response = session.get(url, headers=add_headers, cookies=my_token)  
        xbmc.log("116;URL Get req {0}\r\n".format(str(url)),level=xbmc.LOGERROR)

    elif bearer_in_header:
        response = session.post(url,headers=add_headers, cookies=my_token)  
    else:
        response = session.post(url,headers=add_headers, cookies=my_token, data=put_data)    

    
    if response.status_code < 400:
        return response.json()
    elif response.status_code == 401:  #if the token gives back unauthorized, it's old. Delete it and rerun the method
        os.remove(TOKEN_FILE)
        get_web_data(url)
    else:
        xbmc.log("Could not get data, line 113. Response: {0}\r\nText: {1}".format(response.status_code, response.text),level=xbmc.LOGERROR)
        return None

def change_url_returned_by_home(url, my_title=None):
    """Takes in the url supplied by the homepage returned data, and adds the correct syntax for the web API url 
    """   
    my_website = None
    
    xbmc.log("In change url: {0}".format(url),level=xbmc.LOGERROR)
    
    if my_title == "Replays":
        return { "url" : "https://api.flograppling.com/api/events/completed?future=0", "type" : "previous"}
    
    if my_title == "Live Events":
        
        return { "url" : "https://api.flograppling.com/api/events/today?live_only=1", "type" : "listing"}
    
    
    #try finding collections/number
    my_pattern = "collections\/(\d+)"
    found_collections = re.search(my_pattern,url)
    if found_collections is not None:
        #xbmc.log("\nIn change url: {0}".format(url),level=xbmc.LOGERROR)
        my_website = "https://api.flograppling.com/api/collections/{0}?page=1&limit=25&sort=recent&view=Completed".format(found_collections.group(1))
        #xbmc.log("\nFound collection: {0}".format(my_website),level=xbmc.LOGERROR)
        return_dict =  { "url" : my_website, "type" : "collection"}
        ###Collection has one id, and needs to be drilled down on using the event ID
    
    my_pattern = "events\/(\d+)"
    found_collections = re.search(my_pattern,url)
    if found_collections is not None:   
        my_website = "https://api.flograppling.com/api/events/{0}".format(found_collections.group(1))
        return_dict =  { "url" : my_website, "type" : "event"}
    
    my_pattern = "^\/events$"
    found_collections = re.search(my_pattern,url)
    if found_collections is not None:   
        #xbmc.log("\nIn the place\nIn the place\nIn the place\nIn the place ",level=xbmc.LOGERROR)
        my_website = "https://api.flograppling.com/api/events/timeline?page=1&limit=60&timestamp=1625119398&live_only=0&sort=ascending" 
        #ascending
        
        ###Anthony looking here 19/07/2021
        ###/api/events/timeline?page=1&limit=60&timestamp=1625119398&live_only=0&sort=ascending <--this gets what I want
        return_dict =  { "url" : my_website, "type" : "listing"}     
    
    
    my_pattern = "training$"
    found_collections = re.search(my_pattern,url)
    if found_collections is not None:   
        
        my_website = "https://api.flograppling.com/api/search/?limit=25&published_only=1&sort=recent&type=video&category=Training"
        return_dict =  { "url" : my_website, "type" : "listing"}  
        
    
    my_pattern = "films$"
    found_collections = re.search(my_pattern,url)
    if found_collections is not None:   
        
        my_website = "https://api.flograppling.com/api/search/?limit=25&published_only=1&type=video&category=FloFilm,Documentary&sort=recent&page=1"
        return_dict =  { "url" : my_website, "type" : "listing"}    

    xbmc.log("Return Dict: {0}\n".format(return_dict),level=xbmc.LOGERROR)
    
    return return_dict
    

def build_initial_menu_data(data):
    """Put initial data items in an array of dict, that contains what we need to build
    the inital menu"""
    
    my_initial_menu = []
    
    skip_title = ["Live & Upcoming"]
    
    ###Add a title to the first one, as they miss it 
    data["sections"][0]["title"] = "Shortcuts"
    
    for section in data["sections"]:
        """Go through the web data, and grab all the URL's for the homepage"""
        dictionary_to_add = {}
        description = section["description"]

        if section["items_style"] in 'shortcut':
            for shortcut in section["items"]:
                my_title = shortcut["title"]
                my_url = shortcut["url"]
                
                type_and_url = change_url_returned_by_home(my_url,my_title)
                
                dictionary_to_add = {}
                dictionary_to_add = {
                "type" : type_and_url['type'],
                "title" : my_title,
                "url" : type_and_url['url'],   
                #"url" : my_url,   ###this may be wrong, only applicable for events?
                'thumb': None,
                'icon' : None ,
                'landscape': None ,
                'poster' : None,
                'banner': None,
                'fanart': None
                }
                if not my_title in skip_title: #stop duplicates, and remove unwanted
                    my_initial_menu.append(dictionary_to_add)
                    #xbmc.log("247 Title:{0}, url {1}".format(dictionary_to_add['title'],dictionary_to_add['url']),level=xbmc.LOGERROR)
                    skip_title.append(my_title)
            
        elif section["action"]:
            my_title = section["title"]
            my_url = section["action"]['url']
            type_and_url = change_url_returned_by_home(my_url) ### Redo the url and also find out the type from url
                    
            dictionary_to_add = {
                "type" : type_and_url['type'],
                "title" : my_title,
                "url" : type_and_url['url'],   
                #"url" : my_url,   ###this may be wrong, only applicable for events?
                'thumb': None,
                'icon' : None ,
                'landscape': None ,
                'poster' : None,
                'banner': None,
                'fanart': None
            }
            if not my_title in skip_title: #stop duplicates, and remove unwanted
                my_initial_menu.append(dictionary_to_add)
                #xbmc.log("247 Title:{0}, url {1}".format(dictionary_to_add['title'],dictionary_to_add['url']),level=xbmc.LOGERROR)
                skip_title.append(my_title)
               
        
    
    return my_initial_menu

def get_initial_images():
    """Get images from the local directory to build some backgrounds for the home landing page """
    pass
    
def build_initial_menu():
    """Builds the initial menus for FLOGrappling"""
    
    ###Grab some random pictures from the resources directory
    my_pictures = get_initial_images()
    
    ##Get the web data from the homepage
    data = get_web_data(urls["home"]) 
    
    menu_data = build_initial_menu_data(data)
    

    #xbmc.log("\n\nDict contains: {0}\n\n".format(str(item)),level=xbmc.LOGERROR)


    for item in menu_data:
        #xbmc.log("\nTitle{0}, url {1}".format(item["title"],item["url"]),level=xbmc.LOGERROR)
        kodi_item = xbmcgui.ListItem(label=item['title'])
        info_label = {
                        'title' : item["title"].capitalize()
                        }
        kodi_item.setInfo(type='video', infoLabels=info_label )

        kodi_item.setArt({  'thumb': random.choice(my_pictures),
                               'icon' :  random.choice(my_pictures),
                               'landscape': random.choice(my_pictures),
                               'poster' : random.choice(my_pictures),
                               'banner': random.choice(my_pictures),
                               'fanart': random.choice(my_pictures)})

        url = '{0}?action={1}&u={2}'.format(addon_url, item['type'], quote(item["url"]))
        xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, True ) ###last false if it is a directory

    #### Add the search to the list also:
    kodi_item = xbmcgui.ListItem(label="Search")
    kodi_item.setInfo(type='video', infoLabels={'title': 'Search'})
    url = '{0}?action=search'.format(addon_url)
    xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, True ) ###last false is if it is a directory


    ##create the initial Menu
    xbmcplugin.endOfDirectory(addon_handle)


def get_initial_images():
    """Get a bunch of images for initial build menu"""
    
    files = [file for file in os.listdir(PICTURE_FILES) if not os.path.isdir(file)]
    
    return files    

##
def sort_data_from_dict(item):
    """Create a list of events from the home menu after selecting events. ...Not sure how generalisable this will be"""
    event_data = {
        'id' : item['id'],
        'picture' : item['asset_url'],
        'title' : item["title"],
        'description' : item['seo_description'],
        'preview_text' : item['preview_text'],
        'type' : item["type"]
    }
    return event_data        

def sort_data_from_list(event_data):
    """After Searching for events and selecting an event id, parse the data to output dict with playlist, title and url for 
    pic"""

    my_playable_items = []
    
    if not isinstance(event_data, list):
        event_data = [event_data]
    
    #xbmc.log("\n323Item is: {0}".format(event_data),level=xbmc.LOGERROR)
    for item in event_data:
        
        #xbmc.log("\nItem is: {0}".format(item),level=xbmc.LOGERROR)
        if item['type']  == "video": 
            my_item = {
                "title" : item["title"],
                "playlist": item["playlist"],
                "type" : item["type"],
                #'preview_text' : item['preview_text'],
                "picture" : item["asset_url"]
            }
            my_playable_items.append(my_item)
        
        elif item['type']  == "event" and 'status' in item['live_event']:
            if item['live_event']["status"] == 'CONCLUDED':
                my_item = {
                    "id" : item["id"],
                    "title" : item["title"],
                    "asset_url": item["asset_url"],
                    "type" : item["type"],
                    "picture" : item["asset_url"],
                    'preview_text' : item['preview_text'],
                    "description" : item['seo_description']
                }
            if item['live_event']["status"] == 'LIVE':
                my_item = {
                    "id" : item['live_event']['stream_list'][0]['stream_id'],
                    "title" : "LIVE: " + item["title"],
                    "asset_url": item["asset_url"],
                    "type" : "live",
                    "picture" : item["asset_url"],
                    'preview_text' : "LIVE: " + item['preview_text'],
                    "description" : "LIVE: " + item['seo_description']
                }                
                
                my_playable_items.append(my_item)
            

    return my_playable_items




def build_menu(itemData):     
    """ Takes in array of dict, using this array builds a menu to display in Kodi"""
    
    
    #xbmc.log("\n\Item data is: {0}".format(str(itemData)),level=xbmc.LOGERROR)
    
    if type(itemData) is not list:
        itemData = [itemData]
    
    
    for my_item in itemData:
        
        xbmc.log("\nItem is: {0}".format(str(my_item)),level=xbmc.LOGERROR)
        
        if my_item["type"] == "video":
            xbmc.log("\nThinks it's video\n\n\n",level=xbmc.LOGERROR)
            kodi_item = xbmcgui.ListItem(label=my_item["title"],label2=my_item["title"])
            kodi_item.setArt({  'thumb': my_item["picture"], 
                                'icon' :  my_item["picture"], 
                                'landscape': my_item["picture"], 
                                'poster' : my_item["picture"], 
                                'banner': my_item["picture"], 
                                'fanart': my_item["picture"]})

            video_info = {
                            'plot': my_item.get("description"),
                            'plotoutline' : my_item.get("description"),
                            'tagline' : my_item.get("description"),
                            'setoverview' : my_item.get("description"),
                            'episodeguide' : my_item.get("description"),
                            'mediatype' : "tvshow",
                            'duration': my_item.get("duration")
                           }

            kodi_item.setInfo(type='video', infoLabels=video_info)
                                
            url = '{0}?action=play&i={1}&t={2}'.format(addon_url, my_item["playlist"], quote_plus(my_item["title"].encode('utf8'))) ##added encode utf
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=False, totalItems=len(itemData)) ###last false is if it is a directory
        
        
        
        
        else:
            kodi_item = xbmcgui.ListItem(label=my_item["title"],label2=my_item["title"])

            kodi_item.setArt({  'thumb': my_item["picture"], 
                                'icon' :  my_item["picture"], 
                                'landscape': my_item["picture"], 
                                'poster' : my_item["picture"], 
                                'banner': my_item["picture"], 
                                'fanart': my_item["picture"]})

            #url_for_getting_data = playlist_url.format(my_item["id"]) don't need this just need event id
            url = '{0}?action={2}&u={1}&t={2}'.format(addon_url, my_item['id'], my_item['type'])
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=True, totalItems=len(itemData)) ###last false is if it is a directory 

    ###Thats it create the folder structure
    xbmcplugin.endOfDirectory(addon_handle)


def play_hls_video(m38u_url, v_title):


    #my_encoding = urlencode(headers)
    my_encoding = urlencode(play_live_header)

    playitem = xbmcgui.ListItem(path=m38u_url,label=v_title)
    playitem.setProperty('inputstream', 'inputstream.adaptive')    

    playitem.setMimeType('application/vnd.apple.mpegurl')   ###
    playitem.setProperty('inputstream.adaptive.manifest_type', 'hls')  ###was originally hls, trying mpd          
    
    playitem.setContentLookup(False)
    playitem.setProperty('isFolder', 'false')
    playitem.setProperty('IsPlayable', 'true')
       ###This is needed for kodi 19>
      
    playitem.setProperty('inputstream.adaptive.stream_headers', my_encoding )  

    
    xbmc.log("Stream addr is: {0}".format(str(m38u_url)),level=xbmc.LOGERROR)
    #xbmc.Player().play(stream  ,  playitem)    #### added + "|" + my_encoding
    
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)


def get_data_for_collection(url):
    """Takes in the Id and Grabs the list of videos to populate the menu"""
    data_from_request = get_web_data(url)['data']
    
    #xbmc.log("\collection is: {0}".format(data_from_request),level=xbmc.LOGERROR)
    
    if data_from_request['node_associations']:  ##Return the list inside the collection
        return data_from_request['node_associations']
    
    
    if data_from_request['metadata_filters'] is not None:   
        for item in data_from_request['metadata_filters']:
            if 'event' in item['type']:
                my_id = item['id']
                
    if 'my_id' not in vars():
        
        my_id = data_from_request['id']
        xbmc.log("\n\n\nmy id not in vars\n\n\n",level=xbmc.LOGERROR)
        
    url = "https://api.flograppling.com/api/search/events/{0}/videos?limit=25&page=1)".format(my_id)
    type = "listing"
    
    my_video_list = get_web_data(url)['data']
    
    return my_video_list


def get_data_for_event(url):
    """Takes in the Id from event and gets list of videos to populate the menu"""
    data_from_request = get_web_data(url)['data']
    my_id = data_from_request['id']
    
    url = "https://api.flograppling.com/api/search/events/{0}/videos?limit=25&page=1)".format(my_id)
    type = "listing"
    
    my_video_list = get_web_data(url)['data']
    
    return my_video_list

def get_data_for_listing(url):

    data_from_request = get_web_data(url)['data']
    return data_from_request

def get_live_m38u(stream_id):

    my_url = "https://live-api-3.flosports.tv/streams/{0}/tokens".format(stream_id)
    url_data = get_web_data(my_url,False, True)['data'] # Get the data using authorization: "bearer ....."
    return url_data['cleanUri']


def sort_data_for_previous(url):

    data_from_request = get_web_data(url)['data']
    
    my_array_of_items = []
    
    for item in data_from_request:
        my_item = {
            "title" : item['short_title'],
            "id" : item['id'],
            "picture" : item['asset']['url'],
            "type" : 'listing'
        }
        my_array_of_items.append(my_item)

    return my_array_of_items
    

def router(paramstring):
    """Router for kodi to select the menu item and route appropriately. """ 
    params = dict(parse_qsl(paramstring))
    
    if params:
        action = params['action']
        if action == 'listing':
            #menu_data=global_categoriser(params['u'],action)
            url = unquote(params['u'])
            xbmc.log("List addr is: {0}".format(url),level=xbmc.LOGERROR)
            data = get_data_for_listing(url)  
            sorted_data = sort_data_from_list(data)
            menu_data = sorted_data
            build_menu(menu_data)
        elif action == 'event':
            #url = unquote(params['u'])
            video_list = get_data_for_event(params['u'])           
            menu_data=sort_data_from_list(video_list)
            build_menu(menu_data)
        elif action == 'collection':
            #url = unquote(params['u'])
            video_list_data = get_data_for_collection(params['u'])
            menu_data=sort_data_from_list(video_list_data)
            build_menu(menu_data)               
        elif action == 'live':     
            #url = unquote(params['u'])
            url_m38u = get_live_m38u(params['u'])
            play_hls_video(url_m38u,params['t'])
        
        elif action == 'previous':
            url = unquote(params['u'])
            menu_data = sort_data_for_previous(url)
            
            build_menu(menu_data) 
            #sort through previous listing and return menu
            
            pass
            
        elif action == 'play':
            play_hls_video(params['i'],params['t'])
        elif action == 'search':
            search_term = get_search_term()   
            video_list_data = search(search_term)
            menu_data=sort_data_from_list(video_list_data)
            build_menu(menu_data)        
        else:
            pass
    else:
        build_initial_menu()
###Up to Here

def get_search_term():
    """Get search term to use in search funtion"""
    kb = xbmc.Keyboard('default', 'heading')
    kb.setDefault('')
    kb.setHeading('Search')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        search_term = kb.getText()
        return search_term
    else:
        return


#### For use in search
def search(query_string):
    """Search funtion, takes in keyword for search then returns a list of items that can be used to create the menu"""
    
    encoded_search = quote(query_string)
   
    search_url = """https://api.flograppling.com/api/search/?limit=25&published_only=1&q={0}&page=1&sort=recent""".format(encoded_search)
    

    my_list = get_web_data(search_url)['data']

    return my_list



       

if __name__ == '__main__':     
    router(sys.argv[2][1:])

