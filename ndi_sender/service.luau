-- NDI Sender — headless service.
-- Owns stream state, spawns the helper, polls process state.
-- Widget + shortcut are thin clients on the command/status state channel.

noctalia.setUpdateInterval(250)

local CHECK_TICKS = 8        -- 8 * 250ms = 2s between process probes
local PENDING_GRACE_TICKS = 64  -- ~16s grace for portal popup + gst startup

local HELPER_PATH = "ndi-cast"
local PID_PATH = "~/.local/state/ndi-cast.pid"

local state = "idle"        -- idle | pending | streaming
local isAvailable = false
local tickCount = 0
local pendingTick = 0
local processCheckPending = false
local stateGeneration = 0
local lastStatusKey
local updateDisplay

local function cfg(key)
    return noctalia.getConfig(key)
end

local function publishStatus()
    local key = `{state}/{if isAvailable then "1" else "0"}`
    if key == lastStatusKey then return end
    lastStatusKey = key
    noctalia.state.set("status", { state = state, available = isAvailable })
end

local function setState(nextState)
    if state == nextState then return end
    state = nextState
    stateGeneration += 1
end

local function buildStartCommand()
    local source = cfg("source_type") or "both"
    local cmd = `{HELPER_PATH} --source-type {source}`
    if cfg("restore_portal") then
        cmd = `{cmd} --restore-portal`
    end
    return cmd
end

local function checkAvailability()
    return noctalia.commandExists(HELPER_PATH) and noctalia.commandExists("gst-launch-1.0")
end

local function detectProcessStateAsync(callback)
    -- Pidfile-based detection: helper writes its own PID on start and removes it
    -- on clean exit. `kill -0` probes whether the PID is still alive without
    -- sending any signal. Avoids pgrep self-match against the runAsync sh -c
    -- parent (whose cmdline contains whatever needle we'd pgrep for).
    local probe = `test -e {PID_PATH} && kill -0 $(cat {PID_PATH}) 2>/dev/null`
    noctalia.runAsync(probe, function(r)
        callback(if r.exitCode == 0 then "streaming" else nil)
    end)
end

local function startStream()
    if not isAvailable or state ~= "idle" then return end

    setState("pending")
    pendingTick = 0
    updateDisplay()

    -- noctalia.portalAvailable() scans /proc for the portal daemon, which on
    -- this system is D-Bus activated on demand — it isn't running until the
    -- helper itself invokes a portal method. Skip the pre-check; the helper
    -- surfaces real portal failures clearly through its own error path.

    local cmd = buildStartCommand()
    if not noctalia.runAsync(cmd) then
        setState("idle")
        noctalia.notifyError("NDI sender failed", "Could not launch ndi-cast")
        updateDisplay()
        return
    end
end

local function stopStream()
    if state == "idle" then return end
    local stop = `test -e {PID_PATH} && kill -INT $(cat {PID_PATH}) 2>/dev/null; true`
    noctalia.runAsync(stop)
    setState("idle")
end

local function checkProcessState(processState)
    if state == "pending" then
        pendingTick += CHECK_TICKS
        if processState == "streaming" then
            setState("streaming")
        elseif pendingTick >= PENDING_GRACE_TICKS then
            setState("idle")
            noctalia.notify("NDI sender", "Portal session cancelled or timed out")
        end
    elseif state == "streaming" then
        if processState ~= "streaming" then
            setState("idle")
        end
    elseif state == "idle" then
        if processState == "streaming" then
            -- A stream was started outside the plugin (manual invocation)
            setState("streaming")
        end
    end
end

local function requestProcessStateCheck()
    if processCheckPending then return end
    processCheckPending = true
    local generation = stateGeneration
    detectProcessStateAsync(function(processState)
        processCheckPending = false
        if generation ~= stateGeneration then return end
        checkProcessState(processState)
        updateDisplay()
    end)
end

function updateDisplay()
    publishStatus()
end

function update()
    tickCount += 1

    if tickCount == 1 then
        isAvailable = checkAvailability()
        requestProcessStateCheck()
    end

    if tickCount % CHECK_TICKS == 0 then
        requestProcessStateCheck()
    end

    updateDisplay()
end

function onIpc(event, payload)
    if event == "start" then
        startStream()
    elseif event == "stop" then
        stopStream()
    elseif event == "toggle" then
        if state == "streaming" or state == "pending" then
            stopStream()
        elseif state == "idle" then
            startStream()
        end
    else
        noctalia.log(`ndi_sender: unknown command '{event}'`)
    end
end

noctalia.state.watch("command", function(cmd)
    local action = if type(cmd) == "table" and cmd.action ~= nil then cmd.action else cmd
    if type(action) == "string" then
        onIpc(action, nil)
    end
end)
