const { app, BrowserWindow, ipcMain, screen, globalShortcut, desktopCapturer, dialog } = require('electron')
const path = require('path')
const fs = require('fs')

// 添加配置文件路径
const configPath = path.join(app.getAppPath(), 'config.json');
const defaultConfigPath = path.join(app.getAppPath(), 'default_config.json');

// 更新Live2D模型路径的函数
function updateLive2DModelPath() {
    console.log('开始更新Live2D模型路径...')
    const appDir = app.getAppPath()
    const modelDir = path.join(appDir, '2D') // 指定模型所在的"2D"文件夹
    
    // 检查2D文件夹是否存在
    if (!fs.existsSync(modelDir)) {
        console.log('2D文件夹不存在，不进行更新')
        return
    }
    
    // 查找2D文件夹中的所有.model3.json文件
    let modelFiles = []
    try {
        const files = fs.readdirSync(modelDir)
        modelFiles = files.filter(file => file.endsWith('.model3.json'))
        
        if (modelFiles.length === 0) {
            console.log('2D文件夹中没有找到.model3.json文件，不进行更新')
            return
        }
        
        // 使用第一个找到的模型文件
        const selectedModelFile = modelFiles[0]
        const relativeModelPath = path.join('2D', selectedModelFile).replace(/\\/g, '/') // 使用相对路径，确保使用正斜杠
        console.log(`找到模型文件: ${relativeModelPath}`)
        
        // 读取并更新app.js文件
        const appJsPath = path.join(appDir, 'app.js')
        let jsContent = fs.readFileSync(appJsPath, 'utf8')
        
        // 查找并替换模型路径
        const pattern = /const model = await PIXI\.live2d\.Live2DModel\.from\("([^"]*)"\);/
        const replacement = `const model = await PIXI.live2d.Live2DModel.from("${relativeModelPath}");`
        
        if (pattern.test(jsContent)) {
            // 替换匹配到的内容
            jsContent = jsContent.replace(pattern, replacement)
            
            // 写回文件
            fs.writeFileSync(appJsPath, jsContent, 'utf8')
            console.log(`成功更新app.js文件中的模型路径为: ${relativeModelPath}`)
        } else {
            console.log('在app.js中没有找到匹配的模型加载代码行')
        }
    } catch (err) {
        console.error('更新Live2D模型路径时出错:', err)
    }
}

// 修改后的函数，不再检查配置文件是否存在
function ensureConfigExists() {
    // 假设配置文件一定存在，只记录一条日志
    console.log('使用现有配置文件');
}

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
        focusable: true,
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
        skipTaskbar: true,
        maximizable: false,
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
    
    // 为调试添加开发者工具快捷键
    globalShortcut.register('F12', () => {
        win.webContents.openDevTools();
    });
    
    return win
}

// 在主进程启动时调用
app.whenReady().then(() => {
    // 确保配置文件存在（已修改，现在只打印日志）
    ensureConfigExists();
    
    // 在创建窗口前先更新Live2D模型路径
    updateLive2DModelPath();
    
    const mainWindow = createWindow();
    
    // 添加配置相关的快捷键
    globalShortcut.register('CommandOrControl+,', () => {
        openConfigEditor(mainWindow);
    });
    
    globalShortcut.register('CommandOrControl+Q', () => {
        app.quit();
    });


    // 添加打断功能的全局快捷键
    globalShortcut.register('CommandOrControl+G', () => {
        // 发送中断消息到渲染进程
        const mainWindow = BrowserWindow.getAllWindows()[0];
        if (mainWindow) {
            mainWindow.webContents.send('interrupt-tts');
        }
    });


    globalShortcut.register('CommandOrControl+T', () => {
        const windows = BrowserWindow.getAllWindows();
        windows.forEach(win => {
            win.setAlwaysOnTop(true, 'screen-saver');
        });
    });
});



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

// 修改打开配置编辑器的功能，假设配置文件总是存在
function openConfigEditor(parentWindow) {
    try {
        // 使用系统默认应用打开配置文件
        require('electron').shell.openPath(configPath);
    } catch (error) {
        console.error('打开配置文件失败:', error);
        dialog.showMessageBox(parentWindow, {
            type: 'error',
            title: '错误',
            message: '无法打开配置文件',
            detail: error.message,
            buttons: ['确定']
        });
    }
}

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

// 添加保存配置的IPC处理器
ipcMain.handle('save-config', async (event, configData) => {
    try {
        // 创建备份
        if (fs.existsSync(configPath)) {
            const backupPath = `${configPath}.bak`;
            fs.copyFileSync(configPath, backupPath);
        }
        
        // 保存新配置
        fs.writeFileSync(configPath, JSON.stringify(configData, null, 2), 'utf8');
        
        // 通知用户需要重启应用
        const result = await dialog.showMessageBox({
            type: 'info',
            title: '配置已保存',
            message: '配置已成功保存',
            detail: '需要重启应用以应用新配置。现在重启应用吗？',
            buttons: ['是', '否'],
            defaultId: 0
        });
        
        // 如果用户选择重启
        if (result.response === 0) {
            app.relaunch();
            app.exit();
        }
        
        return { success: true };
    } catch (error) {
        console.error('保存配置失败:', error);
        return { success: false, error: error.message };
    }
});

// 修改获取配置的IPC处理器，假设配置文件总是存在
ipcMain.handle('get-config', async (event) => {
    try {
        const configData = fs.readFileSync(configPath, 'utf8');
        return { success: true, config: JSON.parse(configData) };
    } catch (error) {
        console.error('获取配置失败:', error);
        return { success: false, error: error.message };
    }
});

// 添加打开配置文件的IPC处理器
ipcMain.handle('open-config-editor', async (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    openConfigEditor(win);
    return { success: true };
});

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

// 添加IPC处理器，允许从渲染进程手动更新模型
ipcMain.handle('update-live2d-model', async (event) => {
    try {
        // 调用更新模型的函数
        updateLive2DModelPath()
        
        // 通知渲染进程需要重新加载以应用新模型
        const win = BrowserWindow.fromWebContents(event.sender)
        win.reload()
        
        return { success: true, message: '模型已更新，页面将重新加载' }
    } catch (error) {
        console.error('手动更新模型时出错:', error)
        return { success: false, message: `更新失败: ${error.message}` }
    }
})