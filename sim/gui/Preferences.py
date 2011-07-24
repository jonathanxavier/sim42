"""Loads sim42 gui preferences to a dictionary"""

import os, sys, string
from wxPython.wx import *
from xml.dom import Node, minidom
from sim.solver.Variables import *
from sim import gui

GENERIC_PREF = 'Generic'
GRID_PREF = 'Grid'
PFD_PREF = 'Pfd'

ANYVAL_TYPE_PREF = 'Any value'
COLOUR_TYPE_PREF = 'Colour'
FONT_TYPE_PREF = 'Font'
INT_TYPE_PREF = 'Integer'
FLOAT_TYPE_PREF = 'Float'
TXT_TYPE_PREF = 'Text'
CHOICE_TYPE_PREF = 'Choice'
BOOL_TYPE_PREF = 'Boolean'

FILE_NAME_PREF = 'prefs.xml'


#This is just an XML with default values. To modify active preferences, modify prefs.xml
DefaultXMLString = """<?xml version="1.0" ?>
<Preferences>
	<Generic>
		<Language PreferenceType="Choice" KeyName="lang" Group="Generic">
			<Description>Language to use in messages</Description>
			<Value>English</Value>
		</Language>
		<Decimals PreferenceType="Integer" KeyName="decimals" Group="Grid">
			<Description>Decimals to display in grids</Description>
			<Value>4</Value>
		</Decimals>
		<Units PreferenceType="Choice" KeyName="units" Group="Generic">
			<Description>Default unit set</Description>
			<Value>SI</Value>
		</Units>
	</Generic>
	<PortValues>
		<FixedValues>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkFixed" Group="Grid">
				<Description>Background colour of fixed vals</Description>
				<Red>230</Red>
				<Green>230</Green>
				<Blue>250</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxFixed" Group="Grid">
				<Description>Text colour of fixed vals</Description>
				<Red>255</Red>
				<Green>128</Green>
				<Blue>0</Blue>
			</TextColour>
			<Font PreferenceType="Font" KeyName="fntFixed" Group="Grid">
				<Description>Text font of fixed vals</Description>
				<Size>8</Size>
				<Family>70</Family>
				<Style>90</Style>
				<Weight>92</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</Font>
		</FixedValues>
		<CalculatedValues>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkCalc" Group="Grid">
				<Description>Background colour of calculated vals</Description>
				<Red>152</Red>
				<Green>251</Green>
				<Blue>152</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxCalc" Group="Grid">
				<Description>Text colour of calculated vals</Description>
				<Red>0</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</TextColour>
			<Font PreferenceType="Font" KeyName="fntCalc" Group="Grid">
				<Description>Text font of calculated vals</Description>
				<Size>8</Size>
				<Family>70</Family>
				<Style>90</Style>
				<Weight>90</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</Font>
		</CalculatedValues>
		<PassedValues>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkPass" Group="Grid">
				<Description>Background colour of passed vals</Description>
				<Red>255</Red>
				<Green>215</Green>
				<Blue>0</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxPass" Group="Grid">
				<Description>Text colour of passed vals</Description>
				<Red>0</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</TextColour>
			<Font PreferenceType="Font" KeyName="fntPass" Group="Grid">
				<Description>Text font of passed vals</Description>
				<Size>8</Size>
				<Family>70</Family>
				<Style>90</Style>
				<Weight>90</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</Font>
		</PassedValues>
		<EstimatedValues>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkEst" Group="Grid">
				<Description>Background colour of estimated vals</Description>
				<Red>0</Red>
				<Green>191</Green>
				<Blue>255</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxEst" Group="Grid">
				<Description>Text colour of estimated vals</Description>
				<Red>0</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</TextColour>
			<Font PreferenceType="Font" KeyName="fntEst" Group="Grid">
				<Description>Text font of estimated vals</Description>
				<Size>8</Size>
				<Family>70</Family>
				<Style>93</Style>
				<Weight>90</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</Font>
		</EstimatedValues>
		<UnknownValues>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkUnk" Group="Grid">
				<Description>Background colour of unknown vals</Description>
				<Red>173</Red>
				<Green>173</Green>
				<Blue>173</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxUnk" Group="Grid">
				<Description>Text colour of unknown vals</Description>
				<Red>0</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</TextColour>
			<Font PreferenceType="Font" KeyName="fntUnk" Group="Grid">
				<Description>Text font of unknown vals</Description>
				<Size>8</Size>
				<Family>70</Family>
				<Style>93</Style>
				<Weight>90</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</Font>
		</UnknownValues>
		<WhenWaitingForValues>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkWait" Group="Grid">
				<Description>Background colour of values when waiting for something</Description>
				<Red>255</Red>
				<Green>255</Green>
				<Blue>255</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxWait" Group="Grid">
				<Description>Text colour of values when waiting for something</Description>
				<Red>0</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</TextColour>
		</WhenWaitingForValues>
		<GridLabels>
			<BackgroundColour PreferenceType="Colour" KeyName="clrBkCellLbl" Group="Grid">
				<Description>Background colour of cell labels</Description>
				<Red>192</Red>
				<Green>192</Green>
				<Blue>192</Blue>
			</BackgroundColour>
			<TextColour PreferenceType="Colour" KeyName="clrTxCellLbl" Group="Grid">
				<Description>Text colour of cell labels</Description>
				<Red>255</Red>
				<Green>255</Green>
				<Blue>255</Blue>
			</TextColour>
			<Font PreferenceType="Font" KeyName="fntCellLbl" Group="Grid">
				<Description>Text font of cell labels</Description>
				<Size>10</Size>
				<Family>70</Family>
				<Style>90</Style>
				<Weight>92</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</Font>
		</GridLabels>
	</PortValues>
	<Pfd>
		<Connections>
			<MaterialColour PreferenceType="Colour" KeyName="clrLineMat" Group="Pfd">
				<Description>Line colour for a material connection</Description>
				<Red>0</Red>
				<Green>128</Green>
				<Blue>225</Blue>
			</MaterialColour>
			<MaterialStyle PreferenceType="Integer" KeyName="sLineMat" Group="Pfd">
				<Description>Line style for a material connection</Description>
				<Value>100</Value>
			</MaterialStyle>
			<EnergyColour PreferenceType="Colour" KeyName="clrLineEne" Group="Pfd">
				<Description>Line colour for an energy connection</Description>
				<Red>255</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</EnergyColour>
			<EnergyStyle PreferenceType="Integer" KeyName="sLineEne" Group="Pfd">
				<Description>Line style for an energy connection</Description>
				<Value>100</Value>
			</EnergyStyle>
			<SignalColour PreferenceType="Colour" KeyName="clrLineSig" Group="Pfd">
				<Description>Line colour for a signal connection</Description>
				<Red>225</Red>
				<Green>255</Green>
				<Blue>0</Blue>
			</SignalColour>
			<SignalStyle PreferenceType="Integer" KeyName="sLineSig" Group="Pfd">
				<Description>Line style for a signal connection</Description>
				<Value>102</Value>
			</SignalStyle>
		</Connections>
		<Ports>
			<MaterialColour PreferenceType="Colour" KeyName="clrPortMat" Group="Pfd">
				<Description>Colour for a material port</Description>
				<Red>240</Red>
				<Green>220</Green>
				<Blue>0</Blue>
			</MaterialColour>
			<EnergyColour PreferenceType="Colour" KeyName="clrPortEne" Group="Pfd">
				<Description>Colour for an energy port</Description>
				<Red>255</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</EnergyColour>
			<SignalColour PreferenceType="Colour" KeyName="clrPortSig" Group="Pfd">
				<Description>Colour for a signal port</Description>
				<Red>225</Red>
				<Green>255</Green>
				<Blue>0</Blue>
			</SignalColour>
		</Ports>
		<UnitOperations>
			<NameColour PreferenceType="Colour" KeyName="clrUOName" Group="Pfd">
				<Description>Text colour of unit op names</Description>
				<Red>0</Red>
				<Green>0</Green>
				<Blue>0</Blue>
			</NameColour>
			<NameFont PreferenceType="Font" KeyName="fntUOName" Group="Pfd">
				<Description>Text font of unit op names</Description>
				<Size>8</Size>
				<Family>74</Family>
				<Style>90</Style>
				<Weight>90</Weight>
				<Underlined>0</Underlined>
				<Face>Arial</Face>
			</NameFont>
			<MaterialColour PreferenceType="Colour" KeyName="clrPfd" Group="Pfd">
				<Description>Pfd background color</Description>
				<Red>255</Red>
				<Green>255</Green>
				<Blue>255</Blue>
			</MaterialColour>
		</UnitOperations>
	</Pfd>
</Preferences>
"""

class Preference(object):
    """Object that holds basic information of a preference"""
    def __init__(self, name, val, desc='', group=GENERIC_PREF, type=ANYVAL_TYPE_PREF, choices=[]):
        self.name = name
        self.val = val
        self.group = group
        self.type = type
        self.choices = []
        self.desc = desc


class Preferences(object):
    """Object to administer preferences"""
    def __init__(self):
        self.prefs = {}
        self.ReadFromFile()

    def __del__(self):
        del self.prefs

        
    def GetPref(self, key):
        return self.prefs[keys]


    def GetPrefsDict(self):
        return self.prefs


    def GetPrefVal(self, key, default=None):
        p = self.prefs.get(key, None)
        if p: return p.val
        return default


    def SetPrefVal(self, key, val):
        if self.prefs.has_key(key): self.prefs[key].val = val


    def ReadFromFile(self):
        """Reads the xlm file and load values to dictionary"""
        
        if not os.path.exists(FILE_NAME_PREF): self.LoadDefaultsToFile()

        try:
            doc = minidom.parse(FILE_NAME_PREF)
            self.LoadPreferenceFromNode(doc)
            doc.unlink()
        except:
            #Try again, perhaps file was corrupted
            try:
                #print 'Error reading xml file. Defaults were set'                
                self.LoadDefaultsToFile()
                doc = minidom.parse(FILE_NAME_PREF)
                self.LoadPreferenceFromNode(doc)
                doc.unlink()
            except:
                pass
                #print 'double error'


    def LoadPreferenceFromNode(self, node):
        """Gets a node and try to load a preference into the prefs dictionary"""
        pref = self.CreatePreference(node)
        if pref:
            self.prefs[pref.name] = pref
        else:
            for n in node.childNodes:
                self.LoadPreferenceFromNode(n)
        
    
    def UpdateFile(self):
        """Updates the preferences file wiht current vals of dictionary"""
        p = self.prefs
        
        doc = minidom.Document()

        #main  
        nMain = doc.createElement('Preferences')
        doc.appendChild(nMain)


        #main groups
        nGeneric = doc.createElement('Generic')
        nPortVal = doc.createElement('PortValues')
        nPfd = doc.createElement('Pfd')
        nMain.appendChild(nGeneric)
        nMain.appendChild(nPortVal)
        nMain.appendChild(nPfd)        


        #In the generic node
        nParent = nGeneric
        nodes = []
        nodes.append(self.CreateNode(doc, 'Language', p.get('lang', None)))
        nodes.append(self.CreateNode(doc, 'Decimals', p.get('decimals', None)))
        nodes.append(self.CreateNode(doc, 'Units', p.get('units', None)))
        for n in nodes:
            if n: nParent.appendChild(n)


        #In the port val node
        nParent = doc.createElement('FixedValues')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkFixed', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxFixed', None)))
        nodes.append(self.CreateNode(doc, 'Font', p.get('fntFixed', None)))
        for n in nodes:
            if n: nParent.appendChild(n)
        
        nParent = doc.createElement('CalculatedValues')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkCalc', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxCalc', None)))
        nodes.append(self.CreateNode(doc, 'Font', p.get('fntCalc', None)))
        for n in nodes:
            if n: nParent.appendChild(n)

        nParent = doc.createElement('PassedValues')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkPass', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxPass', None)))
        nodes.append(self.CreateNode(doc, 'Font', p.get('fntPass', None)))
        for n in nodes:
            if n: nParent.appendChild(n)
            
        nParent = doc.createElement('EstimatedValues')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkEst', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxEst', None)))
        nodes.append(self.CreateNode(doc, 'Font', p.get('fntEst', None)))
        for n in nodes:
            if n: nParent.appendChild(n)

        nParent = doc.createElement('UnknownValues')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkUnk', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxUnk', None)))
        nodes.append(self.CreateNode(doc, 'Font', p.get('fntUnk', None)))
        for n in nodes:
            if n: nParent.appendChild(n)
            
        nParent = doc.createElement('WhenWaitingForValues')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkWait', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxWait', None)))
        for n in nodes:
            if n: nParent.appendChild(n)
   

        nParent = doc.createElement('GridLabels')
        nPortVal.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'BackgroundColour', p.get('clrBkCellLbl', None)))
        nodes.append(self.CreateNode(doc, 'TextColour', p.get('clrTxCellLbl', None)))
        nodes.append(self.CreateNode(doc, 'Font', p.get('fntCellLbl', None)))
        for n in nodes:
            if n: nParent.appendChild(n)

            
        #In the pfd node
        nParent = doc.createElement('Connections')
        nPfd.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'MaterialColour', p.get('clrLineMat', None)))
        nodes.append(self.CreateNode(doc, 'MaterialStyle', p.get('sLineMat', None)))
        nodes.append(self.CreateNode(doc, 'EnergyColour', p.get('clrLineEne', None)))
        nodes.append(self.CreateNode(doc, 'EnergyStyle', p.get('sLineEne', None)))
        nodes.append(self.CreateNode(doc, 'SignalColour', p.get('clrLineSig', None)))
        nodes.append(self.CreateNode(doc, 'SignalStyle', p.get('sLineSig', None)))
        for n in nodes:
            if n: nParent.appendChild(n)

        nParent = doc.createElement('Ports')
        nPfd.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'MaterialColour', p.get('clrPortMat', None)))
        nodes.append(self.CreateNode(doc, 'EnergyColour', p.get('clrPortEne', None)))
        nodes.append(self.CreateNode(doc, 'SignalColour', p.get('clrPortSig', None)))
        for n in nodes:
            if n: nParent.appendChild(n)

        nParent = doc.createElement('UnitOperations')
        nPfd.appendChild(nParent)
        nodes = []
        nodes.append(self.CreateNode(doc, 'NameColour', p.get('clrUOName', None)))
        nodes.append(self.CreateNode(doc, 'NameFont', p.get('fntUOName', None)))
        for n in nodes:
            if n: nParent.appendChild(n)
        
        n = self.CreateNode(doc, 'MaterialColour', p.get('clrPfd', None))
        if n: nParent.appendChild(n)

        f = open(FILE_NAME_PREF, 'w')
        self.LocalWriteXML(doc, f, '', '\t', '\n')
        f.close()        
        doc.unlink()


    def LocalWriteXML(self, node, writer, indent="", addindent="", newl=""):
        """Own implementation of writexml, because I don't like TextNodes being written in separate lines"""
        if node.nodeType == node.DOCUMENT_NODE:
            writer.write('<?xml version="1.0" ?>\n')
            if node.childNodes:
                for chNode in node.childNodes:
                    self.LocalWriteXML(chNode, writer,indent,addindent,newl)
        else:
            writer.write(indent+"<" + node.tagName)
            attrs = node._get_attributes()
            a_names = attrs.keys()
            for a_name in a_names:
                writer.write(" %s=\"" % a_name)
                self._LocalWriteData(writer, attrs[a_name].value)
                writer.write("\"")
                
            if node.childNodes:
                chIsTxt = node.childNodes[0].nodeType == node.childNodes[0].TEXT_NODE
                if chIsTxt:
                    writer.write(">")
                    self._LocalWriteData(writer, node.childNodes[0].data)
                    writer.write("</%s>%s" % (node.tagName,newl))
                else:
                    writer.write(">%s"%(newl))
                    for chNode in node.childNodes:
                        self.LocalWriteXML(chNode, writer,indent+addindent,addindent,newl)
                    writer.write("%s</%s>%s" % (indent,node.tagName,newl))
            else:
                writer.write("/>%s"%(newl))

    def _LocalWriteData(self, writer, data):
        """Own implementation of _write_data as it can't be imported"""
        replace = string.replace
        data = replace(data, "&", "&amp;")
        data = replace(data, "<", "&lt;")
        data = replace(data, "\"", "&quot;")
        data = replace(data, ">", "&gt;")
        writer.write(data)
        

    def CreatePreference(self, n):
        """Creates a preference from a node object"""
        if not hasattr(n, 'hasAttribute'): return None
        if not n.hasAttribute('PreferenceType'): return None
        
        name = n.getAttribute('KeyName')
        type = n.getAttribute('PreferenceType')
        group = n.getAttribute('Group')
        choices = []

        nDesc = n.getElementsByTagName('Description')
        try:
            nTxt = nDesc[0].childNodes
            desc = self.GetRelevantText(nTxt)
        except:
            desc= ''

        if type == ANYVAL_TYPE_PREF:
            nVal= n.getElementsByTagName('Value')
            try:
                nTxt = nVal[0].childNodes
                val = self.GetRelevantText(nTxt)
            except:
                val = ''

        elif type == COLOUR_TYPE_PREF:
            nR, nG, nB = n.getElementsByTagName('Red'), n.getElementsByTagName('Green'), n.getElementsByTagName('Blue')
            try:
                nTxtR, nTxtG, nTxtB = nR[0].childNodes, nG[0].childNodes, nB[0].childNodes
                txtR, txtG, txtB = self.GetRelevantText(nTxtR), self.GetRelevantText(nTxtG), self.GetRelevantText(nTxtB)
                val = wxColour(int(txtR), int(txtG), int(txtB))
            except:
                val = wxColour(0, 0, 0)

        elif type == FONT_TYPE_PREF:
            nSize, nFam, nStyle = n.getElementsByTagName('Size'), n.getElementsByTagName('Family'), n.getElementsByTagName('Style')
            nW, nUnd, nFace = n.getElementsByTagName('Weight'), n.getElementsByTagName('Underlined'), n.getElementsByTagName('Face')

            try:
                size = int(self.GetRelevantText(nSize[0].childNodes))
                fam = int(self.GetRelevantText(nFam[0].childNodes))
                style = int(self.GetRelevantText(nStyle[0].childNodes))
                w = int(self.GetRelevantText(nW[0].childNodes))
                und = int(self.GetRelevantText(nUnd[0].childNodes))
                face = str(self.GetRelevantText(nFace[0].childNodes))
                val = wxFont(size, fam, style, w, und, face)
            except:
                val = wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL, false, 'Arial')
    
        elif type == INT_TYPE_PREF:
            nVal= n.getElementsByTagName('Value')
            try:
                nTxt = nVal[0].childNodes
                val = int(self.GetRelevantText(nTxt))
            except:
                val = 0

        elif type == FLOAT_TYPE_PREF:
            nVal= n.getElementsByTagName('Value')
            try:
                nTxt = nVal[0].childNodes
                val = float(self.GetRelevantText(nTxt))
            except:
                val = 0.0

        elif type == TXT_TYPE_PREF:
            nVal= n.getElementsByTagName('Value')
            try:
                nTxt = nVal[0].childNodes
                val = str(self.GetRelevantText(nTxt))
            except:
                val = ''

        elif type == CHOICE_TYPE_PREF:
            nVal= n.getElementsByTagName('Value')
            try:
                nTxt = nVal[0].childNodes
                val = str(self.GetRelevantText(nTxt))
            except:
                val = ''

##            for ch in pref.choices:
##                nCh = doc.CreateElemt('Choice')
##                nCh.appendChild(doc.createTextNode(str(ch)))
##                n.appendChild(nCh)
            
        elif type == BOOL_TYPE_PREF:
            nVal= n.getElementsByTagName('Value')
            try:
                nTxt = nVal[0].childNodes
                val = int(self.GetRelevantText(nTxt))
            except:
                val = 0
            
        else:
            return None
        
        pref = Preference(name, val, desc, group, type, choices)
        
        return pref

    def GetRelevantText(self, TxtNodes):
        """When using prettyxml for saving the file instead of just one TextNode, there are lots, and a lot of them have garbage"""
        s = ''
        for n in TxtNodes:
            if n.nodeType == n.TEXT_NODE:
                s += n.data
        s = s.strip()
        return s


    def CreateNode(self, doc, name, pref):
        """Creates an xml node based on a Preference objet"""
        if not pref: return None

        t = pref.type
        
        n = doc.createElement(name)
        n.setAttribute('PreferenceType', t)
        n.setAttribute('KeyName', pref.name)
        n.setAttribute('Group', pref.group)
        
        nDesc = doc.createElement('Description')
        nDesc.appendChild(doc.createTextNode(pref.desc))
        n.appendChild(nDesc)

        if t == ANYVAL_TYPE_PREF:
            nVal = doc.createElement('Value')
            nVal.appendChild(doc.createTextNode(str(pref.val)))
            n.appendChild(nVal)

        elif t == COLOUR_TYPE_PREF:
            c = pref.val
            
            if not isinstance(c, wxColour): c = wxColour(0, 0, 0)
            r, g, b = c.Red(), c.Green(), c.Blue()
            
            nR, nG, nB = doc.createElement('Red'), doc.createElement('Green'), doc.createElement('Blue')
            nR.appendChild(doc.createTextNode(str(r)))
            nG.appendChild(doc.createTextNode(str(g)))
            nB.appendChild(doc.createTextNode(str(b)))
            
            n.appendChild(nR)
            n.appendChild(nG)
            n.appendChild(nB)

        elif t == FONT_TYPE_PREF:
            f = pref.val
            
            if not isinstance(f, wxFont): f = wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL, false, 'Arial')
            size, fam, style = f.GetPointSize(), f.GetFamily(), f.GetStyle()
            w, und, face = f.GetWeight(), f.GetUnderlined(), f.GetFaceName()
            
            nSize, nFam, nStyle = doc.createElement('Size'), doc.createElement('Family'), doc.createElement('Style')
            nW, nUnd, nFace = doc.createElement('Weight'), doc.createElement('Underlined'), doc.createElement('Face')
            nSize.appendChild(doc.createTextNode(str(size)))
            nFam.appendChild(doc.createTextNode(str(fam)))
            nStyle.appendChild(doc.createTextNode(str(style)))
            nW.appendChild(doc.createTextNode(str(w)))
            nUnd.appendChild(doc.createTextNode(str(und)))
            nFace.appendChild(doc.createTextNode(str(face)))

            n.appendChild(nSize)
            n.appendChild(nFam)
            n.appendChild(nStyle)
            n.appendChild(nW)
            n.appendChild(nUnd)
            n.appendChild(nFace)
            
        elif t == INT_TYPE_PREF:
            nVal = doc.createElement('Value')
            nVal.appendChild(doc.createTextNode(str(pref.val)))
            n.appendChild(nVal)

        elif t == FLOAT_TYPE_PREF:
            nVal = doc.createElement('Value')
            nVal.appendChild(doc.createTextNode(str(pref.val)))
            n.appendChild(nVal)

        elif t == TXT_TYPE_PREF:
            nVal = doc.createElement('Value')
            nVal.appendChild(doc.createTextNode(str(pref.val)))
            n.appendChild(nVal)

        elif t == CHOICE_TYPE_PREF:
            nVal = doc.createElement('Value')
            nVal.appendChild(doc.createTextNode(str(pref.val)))
            n.appendChild(nVal)

            for ch in pref.choices:
                nCh = doc.CreateElemt('Choice')
                nCh.appendChild(doc.createTextNode(str(ch)))
                n.appendChild(nCh)
            
        elif t == BOOL_TYPE_PREF:
            nVal = doc.createElement('Value')
            nVal.appendChild(doc.createTextNode(str(pref.val)))
            n.appendChild(nVal)
            
        else:
            return None

        return n

    
    def LoadDefaultsToFile(self):
        """Update xml file with default info"""
        f = open(FILE_NAME_PREF, 'w')
        f.write(DefaultXMLString)
        f.close()  


##    #Do not use this one!!!! Will get deleted soon
##    def LoadDefaultsFromDict(self):
##        """Load default values to dict and to file"""
##        p = self.prefs
##
##        lst = ['English']
##        try:
##            from sim.solver.Messages import MessageHandler
##            d = MessageHandler.GetSupportedLanguages()
##            if type(d['languages']) == type([]):
##                lst = d['languages']
##        finally:
##            p['lang'] = Preference('lang', "English", 'Language to use in messages', GENERIC_PREF, CHOICE_TYPE_PREF, lst)
##        
##        p['decimals'] = Preference('decimals', 4, 'Decimals to display in grids', GRID_PREF, INT_TYPE_PREF)
##
##        lst = ['SI']
##        try:
##            lst = unitSystem.GetSetNames()
##            if type(lst) != type([]):
##                lst = ['SI']
##        finally:
##            p['units'] = Preference('units', 'SI', 'Default unit set', GENERIC_PREF, CHOICE_TYPE_PREF, lst)
##        
##        #Port values
##        p['clrBkFixed'] = Preference('clrBkFixed', wxColour(230, 230, 250), 'Background colour of fixed vals', GRID_PREF, COLOUR_TYPE_PREF)#Lavender
##        p['clrBkCalc'] = Preference('clrBkCalc', wxColour(152, 251, 152), 'Background colour of calculated vals', GRID_PREF, COLOUR_TYPE_PREF)#Palegreen
##        p['clrBkPass'] = Preference('clrBkPass', wxColour(255, 215, 0), 'Background colour of passed vals', GRID_PREF, COLOUR_TYPE_PREF)#Gold
##        p['clrBkEst'] = Preference('clrBkEst', wxColour(0, 191, 255), 'Background colour of estimated vals', GRID_PREF, COLOUR_TYPE_PREF)#Deep sky blue
##        p['clrBkUnk'] = Preference('clrBkUnk', wxColour(173, 173, 173), 'Background colour of unknown vals', GRID_PREF, COLOUR_TYPE_PREF)#"GREY68"
##
##        p['clrTxFixed'] = Preference('clrTxFixed', wxColour(255, 128, 0), 'Text colour of fixed vals', GRID_PREF, COLOUR_TYPE_PREF)#Orange
##        p['clrTxCalc'] = Preference('clrTxCalc', wxColour(0, 0, 0), 'Text colour of calculated vals', GRID_PREF, COLOUR_TYPE_PREF)#Black
##        p['clrTxPass'] = Preference('clrTxPass', wxColour(0, 0, 0), 'Text colour of passed vals', GRID_PREF, COLOUR_TYPE_PREF)#Black
##        p['clrTxEst'] = Preference('clrTxEst', wxColour(0, 0, 0), 'Text colour of estimated vals', GRID_PREF, COLOUR_TYPE_PREF)#Black
##        p['clrTxUnk'] = Preference('clrTxUnk', wxColour(0, 0, 0), 'Text colour of unknown vals', GRID_PREF, COLOUR_TYPE_PREF)#Black
##
##        p['fntFixed'] = Preference('fntFixed', wxFont(8, wxDEFAULT, wxNORMAL, wxBOLD, false, 'Arial'), 'Text font of fixed vals', GRID_PREF, FONT_TYPE_PREF)
##        p['fntCalc'] = Preference('fntCalc', wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL, false, 'Arial'), 'Text font of calculated vals', GRID_PREF, FONT_TYPE_PREF)
##        p['fntPass'] = Preference('fntPass', wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL, false, 'Arial'), 'Text font of passed vals', GRID_PREF, FONT_TYPE_PREF)
##        p['fntEst'] = Preference('fntEst', wxFont(8, wxDEFAULT, wxITALIC, wxNORMAL, false, 'Arial'), 'Text font of estimated vals', GRID_PREF, FONT_TYPE_PREF)
##        p['fntUnk'] = Preference('fntUnk', wxFont(8, wxDEFAULT, wxITALIC, wxNORMAL, false, 'Arial'), 'Text font of unknown vals', GRID_PREF, FONT_TYPE_PREF)
##   
##        #While waiting for something to happen
##        p['clrBkWait'] = Preference('clrBkWait', wxColour(255, 255, 255), 'Background colour of values when waiting for something', GRID_PREF, COLOUR_TYPE_PREF)
##        p['clrTxWait'] = Preference('clrTxWait', wxColour(0, 0, 0), 'Text colour of values when waiting for something', GRID_PREF, COLOUR_TYPE_PREF)
##
##
##        #Grid labels
##        p['clrBkCellLbl'] = Preference('clrBkCellLbl', wxColour(192, 192, 192), 'Background colour of cell labels', GRID_PREF, COLOUR_TYPE_PREF)
##        p['clrTxCellLbl'] = Preference('clrTxCellLbl', wxColour(255, 255, 255), 'Text colour of cell labels', GRID_PREF, COLOUR_TYPE_PREF)
##        p['fntCellLbl'] = Preference('fntCellLbl', wxFont(10, wxDEFAULT, wxNORMAL, wxBOLD, false, 'Arial'), 'Text font of cell labels', GRID_PREF, FONT_TYPE_PREF)
##
##
##        #Pfd prefs
##        #Line colors
##        p['clrLineMat'] = Preference('clrLineMat', wxColour(0, 128, 225), 'Line colour for a material connection', PFD_PREF, COLOUR_TYPE_PREF)#Blue
##        p['clrLineEne'] = Preference('clrLineEne', wxColour(255, 0, 0), 'Line colour for an energy connection', PFD_PREF, COLOUR_TYPE_PREF)#Red
##        p['clrLineSig'] = Preference('clrLineSig', wxColour(225, 255, 0), 'Line colour for a signal connection', PFD_PREF, COLOUR_TYPE_PREF)#Yellow
##
##        #Line style
##        lstStyles = [wxSOLID, wxTRANSPARENT, wxDOT, wxLONG_DASH, wxSHORT_DASH, wxDOT_DASH, wxSTIPPLE,
##                     wxUSER_DASH, wxBDIAGONAL_HATCH, wxCROSSDIAG_HATCH, wxFDIAGONAL_HATCH, wxCROSS_HATCH,
##                     wxHORIZONTAL_HATCH, wxVERTICAL_HATCH]
##        p['sLineMat'] = Preference('sLineMat', wxSOLID, 'Line style for a material connection', PFD_PREF, INT_TYPE_PREF, lstStyles)
##        p['sLineEne'] = Preference('sLineEne', wxSOLID, 'Line style for an energy connection', PFD_PREF, INT_TYPE_PREF, lstStyles)
##        p['sLineSig'] = Preference('sLineSig', wxLONG_DASH, 'Line style for a signal connection', PFD_PREF, INT_TYPE_PREF, lstStyles)
##        
##        #Port clrs
##        p['clrPortMat'] = Preference('clrPortMat', wxColour(240, 220, 0), 'Colour for a material port', PFD_PREF, COLOUR_TYPE_PREF)
##        p['clrPortEne'] = Preference('clrPortEne', wxColour(255, 0, 0), 'Colour for an energy port', PFD_PREF, COLOUR_TYPE_PREF)#Orange
##        p['clrPortSig'] = Preference('clrPortSig', wxColour(225, 255, 0), 'Colour for a signal port', PFD_PREF, COLOUR_TYPE_PREF)#Yellow
##        
##        #Text
##        p['fntUOName'] = Preference('fntUOName', wxFont(8, wxSWISS, wxNORMAL, wxNORMAL), 'Text font of unit op names', PFD_PREF, FONT_TYPE_PREF)
##        p['clrUOName'] = Preference('clrUOName', wxColour(0, 0, 0), 'Text colour of unit op names', PFD_PREF, COLOUR_TYPE_PREF)#Black
##
##        #Pfd
##        p['clrPfd'] = Preference('clrPfd', wxColour(255, 255, 255), 'Pfd background color', PFD_PREF, COLOUR_TYPE_PREF)#White

prefs = Preferences()

if __name__ == '__main__':
    import sys
##    app = wxPySimpleApp()
##    frame = MaterialPortFrame(None, sys.stdout)
##    frame.Centre(wxBOTH)
##    frame.Show(true)
##    app.MainLoop()
    
