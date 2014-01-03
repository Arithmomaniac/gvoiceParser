import datetime
from copy import deepcopy
import re
import htmlentitydefs
from dateutil import tz
import dateutil.parser
import html5lib

#Contacts
class Contact:
    __slots__ = ['name', 'phonenumber']
    def __init__(self):
        self.phonenumber = None
        self.name = None
    #This function is for debugging purposes. It is too verbose to be the __str__ representation.
    #??? is it?
    def dump(self):
        ''' Returns a string that encodes the information inside the object.'''
        return "%s (%s)" % (self.name, self.phonenumber)
    def __nonzero__(self):
        ''' Returns whether or not the contact is empty'''
        return bool(self.phonenumber) or bool(self.name)
    
    @classmethod
    def from_node(cls, node):
        ''' finds and returns the first contact found beneath the node in the tree'''
        contact_obj = cls()
        #now move on to main exec
        #two places the node could be
        contactnode = node.find(Parser.as_xhtml('.//cite[@class="sender vcard"]/a[@class="tel"]'))
        if not contactnode:
            contactnode = node.find(Parser.as_xhtml('.//div[@class="contributor vcard"]/a[@class="tel"]'))
        #name
        contact_obj.name = contactnode.findtext(Parser.as_xhtml('./span[@class="fn"]'))
        if not contact_obj.name: #If a blank string or none.
            contact_obj.name = None
        #phone number
        contactphonenumber = re.search('\d+', contactnode.attrib['href'])
        if contactphonenumber:
            contact_obj.phonenumber = contactphonenumber.group(0)

        return contact_obj

#Text message
class Text:
    __slots__ = ['contact', 'date', 'text']
    def __init__(self):
        self.contact = Contact()
        self.date = None
        self.text = None
    #This function is for debugging purposes. It is too verbose to be the __str__ representation.
    def dump(self):
        ''' Returns a string that encodes the information inside the object.'''
        return "%s; %s; \"%s\"" % (self.contact.dump(), self.date, self.text)
    
    def __nonzero__(self):
        ''' Returns whether or not there is a text message'''
        return bool(self.date) and bool(self.text)
    
    @classmethod
    def from_node(cls, node):
        textmsg_obj = cls()
        textmsg_obj.contact = Contact.from_node(node)    
        textmsg_obj.date =ParseTools.parse_date(node.find(Parser.as_xhtml('./abbr[@class="dt"]')).attrib["title"])
        # !!! FIX: html decode the text content
        textmsg_obj.text = ParseTools.unescape(node.findtext(Parser.as_xhtml('./q')))
        return textmsg_obj

#Text "conversation"; the outer container for grouped texts (they are stored in HTML this way, too)
class TextConversation:
    __slots__ = ['contact', 'texts']
    def __init__(self):
        self.contact = Contact()
        self.texts = []
    #This function is for debugging purposes. It is too verbose to be the __str__ representation.
    def dump(self):
        ''' Returns a string that encodes the information inside the object.'''
        return  self.contact.dump() + "\n" + "\n".join( "\t" + txt.dump() for txt in self.texts)  
    
    def __len__(self):
        '''How many text messages there are'''
        return len(self.texts)
    
    @classmethod
    def from_node(cls, conversationnode, onewayname): 
        ''' finds and returns the first contact found beneath the node in the tree.
        The onewayname parameter is used to set the contact for outgoing texts when there is no replay'''
        #get node of interest
        conversationnode = conversationnode.find(Parser.as_xhtml('.//div[@class="hChatLog hfeed"]'))
        if not conversationnode:
            return
        #now move on to main exec
        textnodes = conversationnode.findall(Parser.as_xhtml('./div[@class="message"]'))
        #!!! FIX? Why is this necessary?
        if not textnodes:
            return None
        txtConversation_obj = cls()
        for txtNode in textnodes:
            textmsg_obj = Text.from_node(txtNode)
            
            #!!! FIX: Why are we using deepcopy?
            if not txtConversation_obj.contact: #if we don't have a contact for this conversation yet
                    if textmsg_obj.contact.name:    #if contact not self, so it note None
                        txtConversation_obj.contact = deepcopy(textmsg_obj.contact)    #They are other participant
            txtConversation_obj.texts.append(deepcopy(textmsg_obj))
        #If still don't have contact name, add from parameter
        if not txtConversation_obj.contact:
            txtConversation_obj.contact.name = onewayname #Pull fron title. No phone number, but fixed in other finction
        return txtConversation_obj
        
#A phone call
class Call:
    __slots__ = ['contact', 'date', 'duration', 'calltype']
    def __init__(self):
        self.contact = Contact()
        self.date = None
        self.duration = None
        #!!! FIX: enum for  Missed, Placed, Received
        self.calltype = None
    #This function is for debugging purposes. It is too verbose to be the __str__ representation.
    def dump(self):
        ''' Returns a string that encodes the information inside the object.'''
        return "%s\n%s; %s(%s)" % (self.calltype, self.contact.dump(), self.date, self.duration)
    
    def __nonzero__(self):
        ''' Returns whether or not there is a text message'''
        return bool(self.date) and bool(self.calltype)
    
    @classmethod
    def from_node(cls, node):
        ''' finds and returns the first Call found beneath the node in the tree'''
        #zoom in, make sure is the right type
        node = node.find(Parser.as_xhtml('.//div[@class="haudio"]'))
        if not node:
            return None
        if node.find(Parser.as_xhtml('./audio')): #is audio, not call
            return None
        #now move on to main exec        
        call_obj = cls()
        call_obj.contact = Contact.from_node(node)
        #time
        call_obj.date = ParseTools.parse_date(node.find(Parser.as_xhtml('./abbr[@class="published"]')).attrib["title"])
        #duration
        duration_text = node.findtext(Parser.as_xhtml('./abbr[@class="duration"]'))
        if duration_text is not None: #but 0 is OK
            call_obj.duration = ParseTools.parse_time(duration_text)
        call_obj.calltype = ParseTools.get_label(node)
        return call_obj

class Audio:
    __slots__ = ['contact', 'audiotype', 'date', 'duration', 'text', 'confidence', 'filename']
    def __init__(self):
        self.contact = Contact()
        #!!! FIX: Enum ('Voicemail' or 'Recorded')
        self.audiotype = None
        self.date = None
        self.duration = None
        self.text = None        #the text of the recording/voicemail
        self.confidence = None  #confidence of prediction (average of individual words)
        self.filename = None    #filename of audio file
    
    #This function is for debugging purposes. It is too verbose to be the __str__ representation.
    def dump(self):
        ''' Returns a string that encodes the information inside the object.'''
        return "%s\n%s; %s(%s); [%s]%s" % (self.audiotype, self.contact.dump(), self.date, self.duration, self.confidence, self.text)
     
    def __nonzero__(self):
        ''' Returns whether or not there is a text message'''
        return bool(self.audiotype) and bool(self.filename) and bool(self.date)
     
    @classmethod
    #Processes voicemails, recordings
    def from_node(cls, node):
        ''' finds and returns the first Audio object found beneath the node in the tree.
        Properly handles whether it is a recording or whether it is voicemail.'''
        #zoom in, make sure is the right type
        node = node.find(Parser.as_xhtml('.//div[@class="haudio"]'))
        if not node:
            return None
        if not node.find(Parser.as_xhtml('./audio')): #this would be a call
            return None
        #now move on to main exec
        audio_obj = cls()
        audio_obj.contact = Contact.from_node(node)
        audio_obj.duration = ParseTools.parse_time(node.findtext(Parser.as_xhtml('./abbr[@class="duration"]')))
        #recording timestamp determined by end of recording, not beginning as one would expect
        audio_obj.date = ParseTools.parse_date(node.find(Parser.as_xhtml('./abbr[@class="published"]')).attrib["title"])  - audio_obj.duration
        descriptionNode = node.find(Parser.as_xhtml('./span[@class="description"]'))
        if descriptionNode and descriptionNode.findtext(Parser.as_xhtml('./span[@class="full-text"]')):
            #!!! FIX: html decode
            fullText = descriptionNode.findtext(Parser.as_xhtml('./span[@class="full-text"]'))
            if fullText != 'Unable to transcribe this message.':
                audio_obj.text = fullText
            #!!! FIX! use itertools
            confidence_values = descriptionNode.findall(Parser.as_xhtml('./span/span[@class="confidence"]'))
            totalconfid = sum( float(i.findtext('.')) for i in confidence_values )
            audio_obj.confidence = totalconfid / len(confidence_values)
        audio_obj.filename = node.find(Parser.as_xhtml('./audio')).attrib["src"]
        audio_obj.audiotype = ParseTools.get_label(node)
        return audio_obj
##---------------------------

class ParseTools:
    @staticmethod
    #from effbot.org.
    def unescape(text):
        '''Unescapes the HTML entities in a block of text'''
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)

    @staticmethod
    def parse_date (datestring):
        '''Parses a Gvoice-formatted date into a datetime object'''
        returntime = dateutil.parser.parse(datestring).astimezone(tz.tzutc())
        return returntime.replace(tzinfo = None)

    @staticmethod
    def parse_time (timestring):
        '''Parses a duration time-string/tag into a timedelta object'''
        timestringmatch = re.search('(\d\d+):(\d\d):(\d\d)', timestring)
        return datetime.timedelta (
            seconds = int(timestringmatch.group(3)),
            minutes = int(timestringmatch.group(2)),
            hours   = int(timestringmatch.group(1))
        )

    ##------------------------------------

    @staticmethod
    #!!! FEATURE: return Inbox, Starred flags
    def get_label(node):
        ''' Gets a category label for the HTML file '''
        labelNodes = node.findall(Parser.as_xhtml('./div[@class="tags"]/a[@rel="tag"]'))
        validtags = ('placed', 'received', 'missed', 'recorded', 'voicemail') #Valid categories
        for label in (node.attrib['href'].rsplit("#")[1] for node in labelNodes): 
            if label in validtags: #last part of label href is valid label
                return label
        return None
    
##-------------------

class Parser:
    @staticmethod
    def as_xhtml(path):
        ''' turns a regular xpath expression into an XHTML one'''
        return re.sub('/(?=\w)', '/{http://www.w3.org/1999/xhtml}', path)
    
    @classmethod
    def process_file(cls, filename):
        '''gets the gvoiceParser object from a file location'''
        ##BEGIN DEBUG
        #tb = html5lib.getTreeBuilder("etree", implementation=etree.ElementTree)
        #p = html5lib.HTMLParser(tb)
        #with open(filename, 'r') as f: #read the file
        #    tree = p.parse(f, encoding="iso-8859-15")
        ##END DEBUG
        with open(filename, 'r') as f: #read the file
            tree = html5lib.parse(f, encoding="iso-8859-15")
        return cls.process_tree(tree, filename) #do the loading

    @staticmethod
    def process_tree(tree, filename = None):
        '''gets the gvoiceParser object from an element tree'''
        #TEXTS
        # !!! BUG: This does not work for foreign languages. Use filename sintead
        onewayname = tree.findtext(Parser.as_xhtml('.//title'));
        onewayname = onewayname[7::] if onewayname.startswith("Me to ") else None
        #process the text files
        obj = TextConversation.from_node(tree, onewayname)
        if obj: #if text, then done
            return obj
        #CALLS
        obj = Call.from_node(tree)
        if obj: #if text, then done
            return obj
        #AUDIO            
        obj = Audio.from_node(tree)
        if obj: #if text, then done
            return obj
        #should not get this far
        return None
