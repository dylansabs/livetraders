// Function to fetch price for a specific symbol
async function fetchPrice(symbol) {
    try {
        const response = await fetch(`http://127.0.0.1:5700/get_price/${symbol}`);
        if (!response.ok) {
            throw new Error('Network response was not okay');
        }
        const data = await response.json();
        const symbolName = symbol === "JPY=X" ? "USDJPY" : symbol.slice(0, -2);
        document.getElementById(`price-${symbol}`).innerText = `${symbolName}: ${data.price}`;
    } catch (error) {
        const symbolName = symbol === "JPY=X" ? "USDJPY" : symbol.slice(0, -2);
        console.error(`There was a problem fetching the price for ${symbolName}:`, error);
        document.getElementById(`price-${symbol}`).innerText = `${symbolName}: Error fetching data`;
    }
}

async function checkBotRunnning(){
    try{
        const response = await fetch(`http://127.0.0.1:5700/bot_status`)
        if (!response.ok){
            throw new Error("Couldn't fetch current bot status");
        }
        const botStatus = await response.json();
        let running = document.getElementById('bot-running');
        if (botStatus.running){
            running.textContent = `Bot Status: ONLINE`;
        }
        else{
            running.textContent = `Bot Status: OFFLINE`;
        }
    }
    catch(error){
        console.error(error)
    }
}

// Function to start updating prices for specified currency pairs
function startUpdatingPrices(symbols) {
    symbols.forEach(symbol => {
        fetchPrice(symbol);
        setInterval(() => fetchPrice(symbol), 5000);
    });
}

// List of currency pairs to track
const currencyPairs = [
    "JPY=X", "GBPJPY=X", "AUDJPY=X", "AUDCAD=X", "USDCAD=X", 
    "CADJPY=X", "CHFJPY=X", "EURJPY=X", "EURCHF=X", "EURCAD=X", 
    "EURAUD=X", "CADCHF=X", "AUDNZD=X", "AUDCHF=X","BTC-USD"
];

document.getElementById('botToggle').addEventListener('click', function() {
    const button = this;
    const isRunning = button.classList.toggle('stop');

    if (isRunning) {
        // Call API to start the bot
        fetch('http://127.0.0.1:5700/start_bot', { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    button.textContent = 'Stop Bot';
                    console.log('Bot started');
                } else {
                    console.error('Failed to start bot');
                    button.classList.remove('stop'); // Revert to start button
                }
            })
            .catch(error => console.error('Error starting bot:', error));
    } else {
        // Call API to stop the bot
        fetch('http://127.0.0.1:5700/stop_bot', { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    button.textContent = 'Start Bot';
                    console.log('Bot stopped');
                } else {
                    console.error('Failed to stop bot');
                    button.classList.add('stop'); // Revert to stop button
                }
            })
            .catch(error => console.error('Error stopping bot:', error));
    }
});

// Function to fetch the last signal from the server
async function fetchLastSignal() {
    try {
        const response = await fetch('http://127.0.0.1:5700/last_signal');
        if (!response.ok) {
            throw new Error('Network response was not ok ' + response.statusText);
        }
        const data = await response.json();
        
        // Add a timestamp to each signal
        const timestamp = new Date().toLocaleString(); // Get the current time in a readable format
        Object.keys(data).forEach(pair => {
            data[pair].time = timestamp;
        });
        
        updateSignalDisplay(data); // Pass the entire data object
    } catch (error) {
        console.error('Error fetching last signal:', error);
    }
}

// Function to update the signal display
function updateSignalDisplay(signals) {
    const signalDisplay = document.getElementById('signals');
    if (!signalDisplay) {
        console.error('Element with ID "signals" not found');
        return;
    }

    // Create a mapping of current signals to update the display without duplication
    const currentSignals = {};

    // Loop through existing signal elements to keep track of them
    signalDisplay.querySelectorAll('.signal-card').forEach(element => {
        const pair = element.querySelector('.pair').textContent;
        currentSignals[pair] = element;
    });

    // Loop through each signal in the signals object
    for (const [pair, signal] of Object.entries(signals)) {
        const actionText = signal.action === 'buy' ? 'Buy' : signal.action === 'sell' ? 'Sell' : 'Hold';

        let signalElement;
        if (currentSignals[pair]) {
            // Update the existing signal element
            signalElement = currentSignals[pair];
            signalElement.querySelector('.time').textContent = `Time: ${signal.time}`;
            signalElement.querySelector('.algo').textContent = `Timeframe: ${signal.algo}`;
            signalElement.querySelector('.entry').textContent = `Entry: ${signal.entry.toFixed(4)}`;
            signalElement.querySelector('.take-profit').textContent = `Take Profit: ${signal.takeProfit.toFixed(4)}`;
            signalElement.querySelector('.stop-loss').textContent = `Stop Loss: ${signal.stopLoss.toFixed(4)}`;
            signalElement.querySelector('.action').textContent = actionText;
            signalElement.querySelector('.action').className = `action ${signal.action}`;
        } else {
            // Create a new signal element
            signalElement = document.createElement('div');
            signalElement.className = 'signal-card';
            signalElement.innerHTML = `
                <div class="pair">${pair}</div>
                <div class="time">Time: ${signal.time}</div>
                <div class="algo">timeframe: ${signal.algo}</div>
                <div class="entry">Entry: ${signal.entry.toFixed(4)}</div>
                <div class="take-profit">Take Profit: ${signal.takeProfit.toFixed(4)}</div>
                <div class="stop-loss">Stop Loss: ${signal.stopLoss.toFixed(4)}</div>
                <div class="action ${signal.action}">${actionText}</div>
            `;
        }

        // Prepend buy/sell signals to the top and ensure they are not duplicated
        if (signal.action === 'buy' || signal.action === 'sell') {
            if (currentSignals[pair]) {
                signalDisplay.removeChild(signalElement); // Remove from current position
            }
            signalDisplay.insertBefore(signalElement, signalDisplay.firstChild); // Insert at top
        } else {
            if (!currentSignals[pair]) {
                signalDisplay.appendChild(signalElement); // Append new hold signals at the bottom
            }
        }
    }
}


// Call the fetchLastSignal function to retrieve the last signal on page load or when needed
function startPeriodicUpdates() {
    // Fetch the last signal every minute
    fetchLastSignal();
    setInterval(fetchLastSignal, 60000); // 60,000 ms = 1 minute

    // Check bot status every 5 seconds
    checkBotRunnning();
    setInterval(checkBotRunnning, 30000); // 30,000 ms = 30 seconds
}

document.addEventListener('DOMContentLoaded', () => {
    startPeriodicUpdates();
});


// Start updating prices for the specified currency pairs
startUpdatingPrices(currencyPairs);
