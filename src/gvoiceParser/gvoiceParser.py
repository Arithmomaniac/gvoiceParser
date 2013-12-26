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
    #def __init__
    def __init__(self):
        self.phonenumber = None
        self.name = None
    def dump(self): #debug info
        return "%s (%s)" % (self.name, self.phonenumber)
    def test(self): #if has values
        return self.phonenumber != None or self.name != None
    
    @classmethod
    #Finds the first contact contained within a node. Returns it
    def fromNode(cls, node):
        contact_obj = cls()

        #two places the node could be
        contactnode = node.find(Parser.as_xhtml('.//cite[@class="sender vcard"]/a[@class="tel"]'))
        if contactnode is None:
            contactnode = node.find(Parser.as_xhtml('.//div[@class="contributor vcard"]/a[@class="tel"]'))

        #name
        contact_obj.name = contactnode.findtext(Parser.as_xhtml('./span[@class="fn"]'))
        if contact_obj.name != None and len(contact_obj.name) == 0: #If a blank string. Should be an isinstance
            contact_obj.name = None
        #phone number
        contactphonenumber = re.search('\d+', contactnode.attrib['href'])
        if contactphonenumber != None:
            contact_obj.phonenumber = contactphonenumber.group(0)

        return contact_obj

#Text message
class Text:
    __slots__ = ['contact', 'date', 'text']
    def __init__(self):
        self.contact = Contact()
        self.date = None
        self.text = None
    def dump(self):
        return "%s; %s; \"%s\"" % (self.contact.dump(), self.date, self.text)
    @classmethod
    def fromNode(cls, node):
        textmsg_obj = cls()
        textmsg_obj.contact = Contact.fromNode(node)
        
        textmsg_obj.date =ParseTools.parse_date(node.find(Parser.as_xhtml('./abbr[@class="dt"]')).attrib["title"]) #date
        textmsg_obj.text = ParseTools.unescape(node.findtext(Parser.as_xhtml('./q'))) #Text. TO DO: html decoder
        return textmsg_obj

#Text "conversation"; the outer container for grouped texts (they are stored in HTML this way, too)
class TextConversation:
    __slots__ = ['contact', 'texts']
    def __init__(self):
        self.contact = Contact()
        self.texts = []
    def dump(self):
        returnstring = self.contact.dump()
        for i in self.texts:
            returnstring += "\n\t%s" % i.dump()
        return returnstring
    
    @classmethod
    def fromNode(cls, conversationnode, onewayname): #a list of texts, and the title used in special cases
        textnodes = conversationnode.findall(Parser.as_xhtml('./div[@class="message"]'))
        if len(textnodes) == 0: #is actually a text file
            return None
        txtConversation_obj = cls()
        for txtNode in textnodes:
            textmsg_obj = Text.fromNode(txtNode)
            if txtConversation_obj.contact.test() == False: #if we don't have a contact for this conversation yet
                    if textmsg_obj.contact.name != None:    #if contact not self
                        txtConversation_obj.contact = deepcopy(textmsg_obj.contact)    #They are other participant
            txtConversation_obj.texts.append(deepcopy(textmsg_obj))
        if not txtConversation_obj.contact.test():  #Outgoing-only conversations don't contain the recipient's contact info.
            txtConversation_obj.contact.name = onewayname #Pull fron title. No phone number, but fixed in other finction
        return txtConversation_obj
        
#A phone call
class Call:
    __slots__ = ['contact', 'date', 'duration', 'calltype']
    def __init__(self):
        self.contact = Contact()
        self.date = None
        self.duration = None
        self.calltype = None #Missed, Placed, Received
    def dump(self):
        return "%s\n%s; %s(%s)" % (self.calltype, self.contact.dump(), self.date, self.duration)
    
    @classmethod
    #process phone calls. Returns Call object
    def fromNode(cls, node):
        call_obj = cls()
        call_obj.contact = Contact.fromNode(node)
        #time
        call_obj.date = ParseTools.parse_date(node.find(Parser.as_xhtml('./abbr[@class="published"]')).attrib["title"])
        #duration
        duration_text = node.findtext(Parser.as_xhtml('./abbr[@class="duration"]'))
        if duration_text != None:
            call_obj.duration = ParseTools.parse_time(duration_text)
        #Call type (Missed, Recieved, Placed)
        call_obj.calltype = ParseTools.get_label(node)
        return call_obj

class Audio:
    __slots__ = ['contact', 'audiotype', 'date', 'duration', 'text', 'confidence', 'filename']
    def __init__(self):
        self.contact = Contact()
        self.audiotype = None   #'Voicemail' or 'Recorded'
        self.date = None
        self.duration = None
        self.text = None        #the text of the recording/voicemail
        self.confidence = None  #confidence of prediction
        self.filename = None    #filename of audio file
    def dump(self):
        return "%s\n%s; %s(%s); [%s]%s" % (self.audiotype, self.contact.dump(), self.date, self.duration, self.confidence, self.text)
        
    @classmethod
    #Processes voicemails, recordings
    def fromNode(cls, node):
        audio_obj = cls()
        audio_obj.contact = Contact.fromNode(node)
        #time
        #duration
        audio_obj.duration = ParseTools.parse_time(node.findtext(Parser.as_xhtml('./abbr[@class="duration"]')))
        audio_obj.date = ParseTools.parse_date(node.find(Parser.as_xhtml('./abbr[@class="published"]')).attrib["title"]) - datetime.timedelta(0, audio_obj.duration)
        #print audio_obj.date
        #print audio_obj.duration
        descriptionNode = node.find(Parser.as_xhtml('./span[@class="description"]'))
        if descriptionNode != None and len(descriptionNode.findtext(Parser.as_xhtml('./span[@class="full-text"]'))) > 0:
            #fullText
            fullText = descriptionNode.findtext(Parser.as_xhtml('./span[@class="full-text"]')) #TO DO: html decoder
            if fullText != 'Unable to transcribe this message.':
                audio_obj.text = fullText
            #average confidence - read each confidence node (word) and average out results
            confidence_values = descriptionNode.findall(Parser.as_xhtml('./span/span[@class="confidence"]'))
            totalconfid = 0
            for i in confidence_values:
                totalconfid += float(i.findtext('.'))
            audio_obj.confidence = totalconfid / len(confidence_values)
        #location of audio file
        audio_obj.filename = node.find(Parser.as_xhtml('./audio')).attrib["src"]
        #label
        audio_obj.audiotype = ParseTools.get_label(node)
        return audio_obj
##---------------------------

class ParseTools:
    @staticmethod
    #from effbot.org. HTML ParseTools.unescape
    def unescape(text):
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
    #Parses a Gvoice-formatted date into a datetime object
    def parse_date (datestring):
        returntime = dateutil.parser.parse(datestring).astimezone(tz.tzutc())
        return returntime.replace(tzinfo = None)

    @staticmethod
    #Parses the "duration" tag into the number of seconds it encodes
    def parse_time (timestring):
        #what does real pattern really mean
        timestringmatch = re.search('(\d\d+):(\d\d):(\d\d)', timestring)
        seconds = 0
        seconds += int(timestringmatch.group(3))
        seconds += int(timestringmatch.group(2)) * 60
        seconds += int(timestringmatch.group(1)) * 3600
        return seconds

    ##------------------------------------

    @staticmethod
    #Gets a category label from the HTNL file
    #TO DO: return Inbox, Starred flags
    def get_label(node):
        labelNodes = node.findall(Parser.as_xhtml('./div[@class="tags"]/a[@rel="tag"]'))
        validtags = ('placed', 'received', 'missed', 'recorded', 'voicemail') #Valid categories
        for i in labelNodes:
            label = i.attrib['href'].rsplit("#")[1] #last part of href
            if label in validtags:
                return label
        return None
    
##-------------------

class Parser:
    @staticmethod
    def as_xhtml(path):
        return re.sub('/(?=\w)', '/{http://www.w3.org/1999/xhtml}', path)
    
    @classmethod
    def process_file(cls, filename):
        with open(filename, 'r') as f: #read the file
            tree = html5lib.parse(f, encoding="iso-8859-15")
        return cls.process_tree(tree, filename) #do the loading

    @staticmethod
    def process_tree(tree, filename = None):
        #texts
        node = tree.find(Parser.as_xhtml('.//div[@class="hChatLog hfeed"]'))
        if node is not None: #is actually a text file
            #get name from title, in case is one-way correspondence. ToDo: i18n
            onewayname = tree.findtext(Parser.as_xhtml('.//title'));
            onewayname = onewayname[7::] if onewayname.startswith("Me to ") else None
            #process the text files
            obj = TextConversation.fromNode(node, onewayname)
        else:
            #look for call/audio
            node = tree.find(Parser.as_xhtml('.//div[@class="haudio"]'))
            if node.find(Parser.as_xhtml('./audio')) is None: #no audio enclosure. Just the call record
                obj = Call.fromNode(node)
            else: #audio
                obj = Audio.fromNode(node)
        return obj
#        print obj.dump();