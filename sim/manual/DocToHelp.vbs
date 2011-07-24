sub d2hclick()
	dim id, elt, img
	id = window.event.srcelement.id

	if left(id, 1) <> "m" then exit sub

	set elt = document.all("c" & mid(id, 3))
	set img = document.all("mi" & mid(id, 3))

	if elt.style.display = "none" then
		elt.style.display = ""
		img.src = "open.gif"
	else
		elt.style.display = "none"
		img.src = "closed.gif"
	end if

	set elt = nothing
	set img = nothing
end sub

sub window_onload()
	dim id, elt

	for i = 0 to document.all.length - 1
		set elt = document.all(i)

		if left(elt.id, 1) = "c" then
			elt.style.display = "none"

		elseif left(elt.id, 2) = "mi" then
			elt.src = "closed.gif"
		end if
	next
end sub
