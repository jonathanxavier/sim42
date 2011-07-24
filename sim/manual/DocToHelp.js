////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//
// dhtml functions: require IE4 or later
//
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

var POPUP_COLOR = 0xffffe0;

function dthml_popup(url)
{
	// get frame
	var pop = document.all["popupFrame"];
	var sty = pop.style;

	// no url? then hide the popup
	if (url == null || url.length == 0)
	{
		if (window.event.srcElement.id.indexOf("popup_") == -1)
			sty.display = "none";
		return;
	}

	// if this is a frame, use it instead of popping a nested one
	if (window.frameElement != null && window.frameElement.id == "popupFrame")
	{
		pop = window.frameElement;
		pop.src = url;
		return;
	}

	// load url into frame
	pop.src = url;

	// initialize frame size/position
	sty.position  = "absolute";
	sty.border    = "1px solid #cccccc";
	sty.posLeft   = window.event.x + document.body.scrollLeft     - 30000;
	sty.posTop    = window.event.y + document.body.scrollTop + 15 - 30000;
	var wid       = document.body.clientWidth;
	sty.posWidth  = (wid > 500)? wid * 0.6: wid - 20;
	sty.posHeight = 50;

	// wait until the document is loaded to finish positioning
	setTimeout("dthml_popup_position()", 100);
}
	
function dthml_popup_position()
{
	// get frame
	var pop = document.all["popupFrame"];
	var frm = document.frames["popupFrame"];
	var sty = pop.style;

	// hide navigation bar, if present
	var nav = frm.self.document.all["ienav"];
	if (nav != null)
		nav.style.display = "none";

	// set popup color
	frm.self.document.body.style.backgroundColor = POPUP_COLOR;

	// get content size
	sty.display = "block";
	frm.scrollTo(0,1000);
	sty.posHeight = frm.self.document.body.scrollHeight + 20;

	// make content visible
	sty.posLeft  += 30000;
	sty.posTop   += 30000;

	// adjust x position
	if (sty.posLeft + sty.posWidth + 10 - document.body.scrollLeft > document.body.clientWidth)
		sty.posLeft = document.body.clientWidth  - sty.posWidth - 10 + document.body.scrollLeft;

	// if the frame fits below the link, we're done
	if (sty.posTop + sty.posHeight - document.body.scrollTop < document.body.clientHeight)
		return;

	// calculate how much room we have above and below the link
	var space_above = sty.posTop - document.body.scrollTop;
	var space_below = document.body.clientHeight - space_above;
	space_above -= 35;
	space_below -= 20;
	if (space_above < 50) space_above = 50;
	if (space_below < 50) space_below = 50;

	// if the frame fits above or we have a lot more room there, move it up and be done
	if (sty.posHeight < space_above || space_above > 2 * space_below)
	{
		if (sty.posHeight > space_above)
			sty.posHeight = space_above;
		sty.posTop = sty.posTop - sty.posHeight - 30;
		return;
	}

	// adjust frame height to fit below the link
	sty.posHeight = space_below;
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//
// d2h functions: browser-independent
//
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

function d2hie()
{
	var ie = navigator.userAgent.toLowerCase().indexOf("msie");
	return ie != -1 && parseInt(navigator.appVersion) >= 4;
}

function d2hpopup(url)
{
	// use dhtml if we can
	if (d2hie())
	{
		dthml_popup(url);
		return false;
	}

	// use regular popups
	if (url != null && url.length > 0)
	{
		var pop = window.open(url, '_d2hpopup', 'resizable=1,toolbar=0,directories=0,status=0,location=0,menubar=0,height=300,width=400');
		pop.focus();                 // if the popup was already open
		pop.onblur = "self.close()"; // doesn't work, not sure why...
	}

	// and ignore the click
	return false;
}

function d2hwindow(url, name)
{
	if (name != 'main')
	{
		window.open(url, name, 'scrollbars=1,resizable=1,toolbar=0,directories=0,status=0,location=0,menubar=0,height=300,width=400');
		return false;
	}
	return true;
}

function d2hcancel(msg, url, line)
{
	return true;
}

function d2hload()
{
	window.focus();
	window.onerror = d2hcancel;
	if (window.name == '_d2hpopup')
	{
		var major = parseInt(navigator.appVersion);
		if (major >= 4)
		{
			var agent = navigator.userAgent.toLowerCase();
			if (agent.indexOf("msie") != -1)
				document.all.item("ienav").style.display = "none";
			else
				document.layers['nsnav'].visibility = 'hide';
		}
	}
}

// set the backcolor for the popups
function d2hframeload()
{
	if (d2hie() && window.frameElement != null && window.frameElement.id == "popupFrame")
		window.document.body.style.backgroundColor = POPUP_COLOR;
}
