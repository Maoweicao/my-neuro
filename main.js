const { app, BrowserWindow, ipcMain, screen, globalShortcut, desktopCapturer } = require('electron')
const path = require('path')
const fs = require('fs')

function ensureTopMost(win) {
    if (!win.isAlwaysOnTop()) {
        win.setAlwaysOnTop(true, 'screen-saver')
    }
}

function createWindow () {
    const primaryDisplay = screen.getPrimaryDisplay()
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize
    const win = new BrowserWindow({
        width: screenWidth,
        height: screenHeight,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        backgroundColor: '#00000000',
        hasShadow: false,
        focusable: false,
        type: 'desktop',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true,
            zoomFactor: 1.0,
            enableWebSQL: true
        },
        resizable: true,
        movable: true,
        skipTaskbar: false,
        maximizable: false
    })
    win.setAlwaysOnTop(true, 'screen-saver')
    win.setIgnoreMouseEvents(true, { forward: true });
    win.setMenu(null)
    win.setPosition(0, 0)
    win.loadFile('index.html')
    win.on('minimize', (event) => {
        event.preventDefault()
        win.restore()
    })
    win.on('will-move', (event, newBounds) => {
        const { width, height } = primaryDisplay.workAreaSize
        if (newBounds.x < 0 || newBounds.y < 0 || 
            newBounds.x + newBounds.width > width || 
            newBounds.y + newBounds.height > height) {
            event.preventDefault()
        }
    })
    win.on('blur', () => {
        ensureTopMost(win)
    })
    setInterval(() => {
        ensureTopMost(win)
    }, 1000)
    return win
}

app.whenReady().then(() => {
    const mainWindow = createWindow()
    globalShortcut.register('CommandOrControl+Q', () => {
        app.quit()
    })
    globalShortcut.register('CommandOrControl+T', () => {
        const windows = BrowserWindow.getAllWindows()
        windows.forEach(win => {
            win.setAlwaysOnTop(true, 'screen-saver')
        })
    })
})

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
    }
})

ipcMain.on('window-move', (event, { mouseX, mouseY }) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    const [currentX, currentY] = win.getPosition()
    const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize
    let newX = currentX + mouseX
    let newY = currentY + mouseY
    newX = Math.max(-win.getBounds().width + 100, Math.min(newX, screenWidth - 100))
    newY = Math.max(-win.getBounds().height + 100, Math.min(newY, screenHeight - 100))
    win.setPosition(newX, newY)
})

ipcMain.on('set-ignore-mouse-events', (event, { ignore, options }) => {
    BrowserWindow.fromWebContents(event.sender).setIgnoreMouseEvents(ignore, options)
})

ipcMain.on('request-top-most', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    win.setAlwaysOnTop(true, 'screen-saver')
})

// 修改后的截图功能：不再隐藏窗口
ipcMain.handle('take-screenshot', async (event, outputPath) => {
    try {
        // 获取所有屏幕源
        const sources = await desktopCapturer.getSources({ 
            types: ['screen'],
            thumbnailSize: screen.getPrimaryDisplay().workAreaSize
        })
        
        // 通常选择第一个屏幕（主屏幕）
        const primaryScreen = sources[0]
        
        // 确保输出目录存在
        const outputDir = path.dirname(outputPath)
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true })
        }
        
        // 将NativeImage转换为PNG并保存
        fs.writeFileSync(outputPath, primaryScreen.thumbnail.toJPEG(75)); // 75是图片的质量参数，可以调整
        
        return outputPath
    } catch (error) {
        console.error('截图错误:', error)
        throw error
    }
})