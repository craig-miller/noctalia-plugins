--!nonstrict
-- Next Event — headless service.
-- Derives khal's calendar set from Noctalia's configured local-vdir accounts,
-- then publishes the next timed event through noctalia.state.

local pluginDir = noctalia.pluginDir()
local command = { "/usr/bin/python3", pluginDir .. "/next_event.py" }
local inFlight = false

local function publish(text, tooltip, ok)
    noctalia.state.set("event", {
        text = text,
        tooltip = tooltip or text,
        ok = if ok == false then false else true,
    })
end

local function refresh()
    if inFlight then
        return
    end

    inFlight = true
    noctalia.runAsync(command, function(result)
        inFlight = false

        if result.exitCode ~= 0 then
            publish("Calendar unavailable", "Noctalia vdir query failed", false)
            noctalia.log("Noctalia next-event query failed: " .. (result.stderr or ""))
            return
        end

        local event, err = noctalia.json.decode(result.stdout or "")
        if event == nil then
            publish("Calendar unavailable", "Invalid next-event response", false)
            noctalia.log("Noctalia next-event JSON failed: " .. (err or "unknown error"))
            return
        end

        publish(event.text or "No events today", event.tooltip, event.ok)
    end)
end

noctalia.setUpdateInterval(60000)
publish("Loading calendar…", "Reading Noctalia vdir calendars", true)
refresh()

function update()
    refresh()
end
