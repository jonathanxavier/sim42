"""Creates a panel used to change settings of a mat stream

Classes:
UOMainPanel -- Main panel for the stream

Functions:
UOWrapperPanel -- Creates the panel and passes it as a return value

"""

import guiUnitOperations

class UOMainPanel(guiUnitOperations.UOMainPanel):
    """This panel puts together all the req panels in the correct place"""
    def __init__(self, parent, interpParent, uOpName, pfd, panelId = -1):
        guiUnitOperations.UOMainPanel.__init__(self, parent, interpParent,
                                                uOpName, pfd, panelId = -1)


def UOWrapperPanel(parent, interpParent, uOpName, pfd):
    """Creates the panel and passes it as a return value"""
    #Empty panel... Overload this function for each specific UO
    return UOMainPanel(parent, interpParent, uOpName, pfd)