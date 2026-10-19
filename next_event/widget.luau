--!nonstrict
-- Next Event — bar widget.
-- Displays the short label published by service.luau.

local event = noctalia.state.get("event") or {
    text = "Loading calendar…",
    tooltip = "Reading Noctalia vdir calendars",
    ok = true,
}

local function render()
    local ok = if event.ok == false then false else true

    barWidget.setGlyph("calendar-event")
    barWidget.setText(event.text or "No more events today")
    barWidget.setTooltip(event.tooltip or event.text or "Next calendar event")
    barWidget.setGlyphColor(if ok then "on_surface" else "error")
    barWidget.setVisible(true)
end

noctalia.state.watch("event", function(value)
    if type(value) == "table" then
        event = value
        render()
    end
end)

function update()
    noctalia.setUpdateInterval(60000)
    render()
end

render()
