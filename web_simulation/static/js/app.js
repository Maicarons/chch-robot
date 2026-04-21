// Web仿真环境前端逻辑

class ChessSimulation {
    constructor() {
        this.apiBase = 'http://localhost:5000/api';
        this.currentState = null;
        this.moveHistory = [];
        this.currentInputSource = 'camera'; // 当前输入源
        this.networkCameraUrl = '';
        this.localImageBase64 = null;
        this.boardState = {}; // 用于可视化棋盘的状态 {"col,row": "piece_char"}
        this.selectedSquare = null; // 当前选中的格子
        this.playerColor = 'red'; // 玩家执红
        this.aiColor = 'black';   // AI执黑
        this.isPlayerTurn = true; // 是否轮到玩家
        this.useManualBoardState = false; // 是否使用手动维护的棋盘状态
        this.init();
    }

    init() {
        this.log('系统初始化...', 'info');
        this.bindEvents();
        this.checkConnection();
        this.updateStatus();
    }

    // 绑定事件
    bindEvents() {
        document.getElementById('btn-capture').addEventListener('click', () => this.captureImage());
        document.getElementById('btn-recognize').addEventListener('click', () => this.recognizeBoard());
        document.getElementById('btn-start-game').addEventListener('click', () => this.startGame());
        document.getElementById('btn-reset-game').addEventListener('click', () => this.resetGame());
        document.getElementById('btn-ai-move').addEventListener('click', () => this.getAIMove());
        document.getElementById('btn-simulate-move').addEventListener('click', () => this.simulateRobotMove());
        document.getElementById('btn-test-sequence').addEventListener('click', () => this.testRobotSequence());
        
        // 网络摄像头连接按钮
        document.getElementById('btn-connect-network').addEventListener('click', () => this.connectNetworkCamera());
        
        // 可视化棋盘点击事件
        document.getElementById('visual-board').addEventListener('click', (e) => this.handleBoardClick(e));
        
        // 定期检查摄像头状态
        setInterval(() => this.checkCameraStatus(), 5000);
    }
    
    // 启用/禁用识别按钮
    setRecognizeButtonEnabled(enabled) {
        const btn = document.getElementById('btn-recognize');
        if (enabled) {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
        }
    }

    // 切换输入源
    changeInputSource() {
        const source = document.getElementById('input-source').value;
        this.currentInputSource = source;
        
        // 隐藏所有输入组
        document.getElementById('network-camera-input').style.display = 'none';
        document.getElementById('local-image-input').style.display = 'none';
        
        // 显示对应的输入组
        if (source === 'network') {
            document.getElementById('network-camera-input').style.display = 'flex';
            this.log('切换到网络摄像头模式', 'info');
        } else if (source === 'local') {
            document.getElementById('local-image-input').style.display = 'flex';
            this.log('切换到本地图片模式', 'info');
        } else {
            this.log('切换到本地摄像头模式', 'info');
        }
    }

    // 连接网络摄像头
    async connectNetworkCamera() {
        const url = document.getElementById('network-camera-url').value.trim();
        
        if (!url) {
            this.log('请输入网络摄像头URL', 'warning');
            return;
        }
        
        this.networkCameraUrl = url;
        this.log(`正在连接网络摄像头: ${url}`, 'info');
        
        // 尝试加载网络摄像头画面
        const img = document.getElementById('camera-feed');
        img.src = url;
        
        img.onload = () => {
            this.log('网络摄像头连接成功', 'info');
        };
        
        img.onerror = () => {
            this.log('网络摄像头连接失败，请检查URL', 'error');
        };
    }

    // 处理本地图片上传
    handleLocalImageUpload(event) {
        const file = event.target.files[0];
        
        if (!file) {
            return;
        }
        
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            this.log('请选择图片文件', 'error');
            return;
        }
        
        const reader = new FileReader();
        
        reader.onload = (e) => {
            this.localImageBase64 = e.target.result;
            
            // 显示图片
            const img = document.getElementById('camera-feed');
            img.src = this.localImageBase64;
            
            this.log(`已加载本地图片: ${file.name}`, 'info');
        };
        
        reader.readAsDataURL(file);
    }

    // 检查连接
    async checkConnection() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            if (response.ok) {
                this.updateConnectionStatus(true);
                this.log('连接到服务器成功', 'info');
            } else {
                this.updateConnectionStatus(false);
            }
        } catch (error) {
            this.updateConnectionStatus(false);
            this.log(`连接失败: ${error.message}`, 'error');
        }
    }

    // 检查摄像头状态
    async checkCameraStatus() {
        try {
            const response = await fetch(`${this.apiBase}/camera/status`);
            const data = await response.json();
            
            if (data.success) {
                if (!data.camera_opened) {
                    this.log('摄像头未打开，尝试自动启动...', 'warning');
                    await this.startCamera();
                }
            }
        } catch (error) {
            // 静默失败，不干扰用户
        }
    }

    // 启动摄像头
    async startCamera() {
        try {
            const response = await fetch(`${this.apiBase}/camera/start`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.log('摄像头启动成功', 'info');
            } else {
                this.log(`摄像头启动失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.log(`启动摄像头错误: ${error.message}`, 'error');
        }
    }

    // 更新连接状态
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (connected) {
            statusEl.textContent = '● 已连接';
            statusEl.className = 'status-indicator connected';
        } else {
            statusEl.textContent = '● 未连接';
            statusEl.className = 'status-indicator disconnected';
        }
    }

    // 捕获图像
    async captureImage() {
        this.log('正在捕获图像...', 'info');
        
        // 如果是本地图片，直接使用已加载的图片
        if (this.currentInputSource === 'local') {
            if (this.localImageBase64) {
                this.log('使用已加载的本地图片', 'info');
                return;
            } else {
                this.log('请先上传本地图片', 'warning');
                return;
            }
        }
        
        // 如果是网络摄像头，已经通过URL加载
        if (this.currentInputSource === 'network') {
            this.log('使用网络摄像头画面', 'info');
            return;
        }
        
        // 本地摄像头模式
        try {
            const response = await fetch(`${this.apiBase}/capture`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ camera_index: 0 })
            });

            const data = await response.json();
            
            if (data.success) {
                const img = document.getElementById('camera-feed');
                img.src = `data:image/jpeg;base64,${data.image}`;
                this.log('图像捕获成功', 'info');
            } else {
                this.log(`捕获失败: ${data.error}`, 'error');
                // 如果是摄像头问题，尝试重启
                if (data.error.includes('摄像头') || data.error.includes('无法捕获')) {
                    this.log('尝试重新启动摄像头...', 'warning');
                    await this.startCamera();
                }
            }
        } catch (error) {
            this.log(`捕获图像错误: ${error.message}`, 'error');
        }
    }

    // 识别棋盘
    async recognizeBoard() {
        // 如果游戏正在进行中，禁止识别
        if (this.moveHistory.length > 0) {
            this.log('⛔ 游戏进行中，禁止手动识别棋盘！', 'error');
            this.log('系统已通过UCI走法自动维护棋盘状态', 'info');
            alert('游戏已开始，不能手动识别棋盘！\n\n棋盘状态由系统通过UCI走法自动维护，手动识别会破坏游戏状态。');
            return;
        }
        
        this.log('正在识别棋盘...', 'info');
        
        let imageData = null;
        
        // 如果是本地图片，发送base64数据
        if (this.currentInputSource === 'local') {
            if (!this.localImageBase64) {
                this.log('请先上传本地图片', 'warning');
                return;
            }
            // 移除 data:image/jpeg;base64, 前缀
            imageData = this.localImageBase64.split(',')[1];
            this.log('使用本地图片进行识别', 'info');
        }
        
        try {
            const response = await fetch(`${this.apiBase}/recognize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: imageData })
            });

            const data = await response.json();
            
            if (data.success) {
                document.getElementById('fen-display').value = data.fen || '';
                document.getElementById('piece-count').textContent = data.piece_count || 0;
                this.log(`识别成功: 检测到 ${data.piece_count} 个棋子`, 'info');
                
                // 更新可视化棋盘
                this.boardState = data.board_state;
                this.drawVisualBoard();
                this.updateGameStatus();
                
                // 绘制原始棋盘检测结果
                this.drawBoard(data.board_state);
            } else {
                this.log(`识别失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.log(`识别错误: ${error.message}`, 'error');
        }
    }

    // 开始游戏
    async startGame() {
        this.log('开始新游戏...', 'info');
        try {
            const response = await fetch(`${this.apiBase}/game/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    use_recognized_board: this.boardState && Object.keys(this.boardState).length > 0,
                    board_state: this.boardState
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.log('游戏已开始 - 玩家执红先行，AI执黑后手', 'info');
                document.getElementById('game-status').textContent = '轮到红方（玩家）';
                document.getElementById('game-status').style.color = '#dc2626';
                this.moveHistory = [];
                this.isPlayerTurn = true; // 玩家先手
                this.updateMoveList();
                
                // 禁用识别按钮
                this.setRecognizeButtonEnabled(false);
                this.log('⛔ 已禁用识别按钮（游戏进行中不允许手动识别）', 'warning');
                
                // 如果有识别的棋盘状态，使用它；否则使用标准布局
                if (data.use_recognized_board && data.board_state) {
                    this.log('🔄 使用识别的棋盘布局...', 'info');
                    this.boardState = data.board_state;
                    this.log('✅ 识别布局已加载，棋子数量: ' + Object.keys(this.boardState).length, 'info');
                } else {
                    this.log('🔄 初始化标准棋盘布局...', 'info');
                    this.initStandardBoard();
                }
                
                this.log('✅ 棋盘状态:', 'info');
                this.log(JSON.stringify(this.boardState), 'info');
            } else {
                this.log(`开始失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.log(`开始游戏错误: ${error.message}`, 'error');
        }
    }

    // 重置游戏
    async resetGame() {
        this.log('重置游戏...', 'info');
        try {
            const response = await fetch(`${this.apiBase}/game/reset`, {
                method: 'POST'
            });

            const data = await response.json();
            
            if (data.success) {
                this.log('游戏已重置', 'info');
                document.getElementById('game-status').textContent = '等待开始';
                document.getElementById('fen-display').value = '';
                document.getElementById('piece-count').textContent = '0';
                this.moveHistory = [];
                this.updateMoveList();
                
                // 重新启用识别按钮
                this.setRecognizeButtonEnabled(true);
                this.log('✅ 已启用识别按钮', 'info');
            } else {
                this.log(`重置失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.log(`重置游戏错误: ${error.message}`, 'error');
        }
    }

    // 获取AI走法
    async getAIMove() {
        if (this.isPlayerTurn) {
            this.log('当前是红方回合，请玩家先走棋', 'warning');
            return;
        }
        
        this.log('AI正在思考...', 'info');
        document.getElementById('game-status').textContent = 'AI思考中...';
        
        const depth = parseInt(document.getElementById('ai-depth').value) || 15;
        const fen = document.getElementById('fen-display').value;

        try {
            const response = await fetch(`${this.apiBase}/ai_move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fen, depth })
            });

            const data = await response.json();
            
            if (data.success) {
                this.log(`AI走法: ${data.move}`, 'info');
                this.moveHistory.push(data.move);
                this.updateMoveList();
                
                // 更新FEN显示
                if (data.fen) {
                    document.getElementById('fen-display').value = data.fen;
                    this.log(`新FEN: ${data.fen}`, 'info');
                }
                
                // 显示分析结果
                if (data.analysis) {
                    this.showAnalysis(data.analysis);
                }
                
                // 执行机械臂移动（传入AI返回的走法）
                await this.executeRobotMove(data.move);
                
                // 更新回合状态
                this.isPlayerTurn = data.is_player_turn || false;
                this.updateGameStatus();
                
                document.getElementById('game-status').textContent = 'AI已走棋，轮到红方';
            } else {
                this.log(`AI走法失败: ${data.error}`, 'error');
                document.getElementById('game-status').textContent = 'AI走法失败';
            }
        } catch (error) {
            this.log(`获取AI走法错误: ${error.message}`, 'error');
            document.getElementById('game-status').textContent = '错误';
        }
    }

    // 执行机械臂移动
    async executeRobotMove(move) {
        this.log(`机械臂执行AI走法: ${move}`, 'info');
        document.getElementById('robot-state').textContent = '移动中...';
        
        try {
            const response = await fetch(`${this.apiBase}/simulate_robot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ move })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.log('机械臂移动完成', 'info');
                document.getElementById('robot-state').textContent = '空闲';
                
                // 解析UCI走法并更新可视化棋盘
                this.updateBoardFromUCIMove(move, true);  // AI走法
                
                this.animateRobotMove(move);
            } else {
                this.log(`移动失败: ${data.error}`, 'error');
                document.getElementById('robot-state').textContent = '错误';
            }
        } catch (error) {
            this.log(`机械臂移动错误: ${error.message}`, 'error');
            document.getElementById('robot-state').textContent = '错误';
        }
    }

    // 根据UCI走法更新棋盘状态
    updateBoardFromUCIMove(uciMove, isAIMove = false) {
        if (uciMove.length < 4) return;
            
        const files = 'abcdefghi';
        // 尝试两种UCI坐标系统：
        // 方案1: UCI排名0=红方底线, 9=黑方底线 → array_row = 9 - uci_rank
        // 方案2: UCI排名0=黑方底线, 9=红方底线 → array_row = uci_rank
        
        const fromFile = uciMove.charAt(0);
        const fromRank = uciMove.charAt(1);
        const toFile = uciMove.charAt(2);
        const toRank = uciMove.charAt(3);
            
        const fromCol = files.indexOf(fromFile);
        const toCol = files.indexOf(toFile);
        
        // 先尝试方案1（反转）
        let fromRow = 9 - parseInt(fromRank);
        let toRow = 9 - parseInt(toRank);
        
        let fromKey = `${fromCol},${fromRow}`;
        let toKey = `${toCol},${toRow}`;
        
        this.log(`🔍 调试: UCI=${uciMove}, 方案1(反转): (${fromCol},${fromRow}) -> (${toCol},${toRow})`, 'info');
        this.log(`🔍 方案1起始位置棋子: ${this.boardState[fromKey] || '空'}`, 'info');
        
        // 检查起始位置是否有棋子
        if (!this.boardState[fromKey]) {
            // 方案1失败，尝试方案2（不反转）
            fromRow = parseInt(fromRank);
            toRow = parseInt(toRank);
            fromKey = `${fromCol},${fromRow}`;
            toKey = `${toCol},${toRow}`;
            
            this.log(`⚠️ 方案1失败，尝试方案2(不反转): ${uciMove} -> (${fromCol},${fromRow}) -> (${toCol},${toRow})`, 'warning');
            this.log(`🔍 方案2起始位置棋子: ${this.boardState[fromKey] || '空'}`, 'info');
            
            // 如果方案2也失败，输出所有棋子位置供调试
            if (!this.boardState[fromKey]) {
                this.log(`❌ 两种方案都失败！列出所有棋子位置:`, 'error');
                Object.entries(this.boardState).forEach(([key, piece]) => {
                    const [c, r] = key.split(',');
                    this.log(`   (${c},${r}): ${piece}`, 'info');
                });
            }
        } else {
            this.log(`✅ 使用方案1（反转）`, 'info');
        }
            
        if (fromCol === -1 || fromRow < 0 || fromRow > 9 || toCol === -1 || toRow < 0 || toRow > 9) {
            this.log(`❌ 无效的UCI走法: ${uciMove}`, 'error');
            return;
        }
            
        this.log(`UCI解析: ${uciMove} -> (${fromCol},${fromRow}) -> (${toCol},${toRow})`, 'info');
        
        // 检查目标位置是否有棋子（吃子）
        const capturedPiece = this.boardState[toKey];
        if (capturedPiece) {
            this.log(`⚔️ 吃子！${capturedPiece} 在 (${toCol},${toRow}) 被吃掉`, 'warning');
            
            // 检查是否是将/帅被吃
            if (capturedPiece === 'K' || capturedPiece === 'k') {
                this.log(`🏆 游戏结束！${capturedPiece === 'K' ? '红方' : '黑方'}被将死！`, 'error');
                alert(`游戏结束！${capturedPiece === 'K' ? '红方（你）' : '黑方（AI）'}被将死！`);
                return;
            }
        }
            
        // 获取移动的棋子
        const piece = this.boardState[fromKey];
        if (!piece) {
            this.log(`❌ 起始位置没有棋子: ${fromKey}`, 'error');
            this.log(`当前棋盘状态:`, 'info');
            this.log(JSON.stringify(this.boardState), 'info');
            this.log(`期望的棋子应该在 (${fromCol},${fromRow})，但实际不存在`, 'error');
            return;
        }
        
        // 检查是否是AI走了玩家的棋子（红方大写）
        if (isAIMove && piece === piece.toUpperCase() && piece !== 'K') {  // 大写=红方，且不是帅
            this.log(`🚨 AI错误：AI操控了红方棋子 ${piece}！`, 'error');
            this.log(`💀 游戏结束！AI失控，你输了！`, 'error');
            alert('AI出现严重错误，操控了你的棋子！\n\n你输了！');
            return;
        }
            
        // 执行移动
        delete this.boardState[fromKey];
        this.boardState[toKey] = piece;
            
        this.log(`✅ 棋盘更新: ${piece} ${fromKey} -> ${toKey}`, 'info');
        this.drawVisualBoard();
    }

    // 模拟机械臂移动
    async simulateRobotMove() {
        if (this.moveHistory.length === 0) {
            this.log('没有可执行的走法', 'warning');
            return;
        }

        const lastMove = this.moveHistory[this.moveHistory.length - 1];
        await this.executeRobotMove(lastMove);
    }

    // 测试机械臂序列
    async testRobotSequence() {
        this.log('执行机械臂测试序列...', 'info');
        document.getElementById('robot-state').textContent = '测试中...';
        
        // 简单模拟
        setTimeout(() => {
            this.log('测试序列完成', 'info');
            document.getElementById('robot-state').textContent = '空闲';
            this.drawRobotVisualization();
        }, 2000);
    }

    // 更新走法列表
    updateMoveList() {
        const moveList = document.getElementById('move-list');
        moveList.innerHTML = '';
        
        this.moveHistory.forEach((move, index) => {
            const moveItem = document.createElement('div');
            moveItem.className = 'move-item';
            moveItem.textContent = `${Math.floor(index / 2) + 1}. ${move}`;
            moveList.appendChild(moveItem);
        });
        
        moveList.scrollTop = moveList.scrollHeight;
    }

    // 显示AI分析
    showAnalysis(analysis) {
        const analysisDiv = document.getElementById('ai-analysis');
        let html = '<h4>AI分析结果</h4>';
        
        if (analysis.best_move) {
            html += `<p><strong>最佳走法:</strong> ${analysis.best_move}</p>`;
        }
        if (analysis.score !== null && analysis.score !== undefined) {
            html += `<p><strong>评估分数:</strong> ${analysis.score}</p>`;
        }
        if (analysis.depth) {
            html += `<p><strong>搜索深度:</strong> ${analysis.depth}</p>`;
        }
        if (analysis.pv) {
            html += `<p><strong>PV线:</strong> ${analysis.pv.substring(0, 50)}...</p>`;
        }
        
        analysisDiv.innerHTML = html;
    }

    // 绘制棋盘
    drawBoard(boardState) {
        const canvas = document.getElementById('board-canvas');
        const ctx = canvas.getContext('2d');
        
        // 清空画布
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!boardState) return;
        
        // 绘制棋子
        const cellWidth = canvas.width / 9;
        const cellHeight = canvas.height / 10;
        
        Object.entries(boardState).forEach(([posKey, side]) => {
            // posKey 格式: "col,row"
            const [col, row] = posKey.split(',').map(Number);
            const x = col * cellWidth + cellWidth / 2;
            const y = row * cellHeight + cellHeight / 2;
            
            // 绘制棋子圆圈
            ctx.beginPath();
            ctx.arc(x, y, 18, 0, Math.PI * 2);
            ctx.fillStyle = side === 'red' ? '#fee2e2' : '#d1d5db';
            ctx.fill();
            ctx.strokeStyle = side === 'red' ? '#ef4444' : '#000000';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // 绘制标签
            ctx.fillStyle = side === 'red' ? '#dc2626' : '#ffffff';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(side === 'red' ? 'R' : 'B', x, y);
        });
    }

    // 绘制机械臂可视化
    drawRobotVisualization() {
        const canvas = document.getElementById('robot-canvas');
        const ctx = canvas.getContext('2d');
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // 绘制简化的机械臂
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 3;
        
        // 基座
        ctx.beginPath();
        ctx.arc(200, 350, 30, 0, Math.PI * 2);
        ctx.stroke();
        
        // 臂段1
        ctx.beginPath();
        ctx.moveTo(200, 350);
        ctx.lineTo(200, 250);
        ctx.stroke();
        
        // 臂段2
        ctx.beginPath();
        ctx.moveTo(200, 250);
        ctx.lineTo(250, 200);
        ctx.stroke();
        
        // 夹爪
        ctx.beginPath();
        ctx.moveTo(250, 200);
        ctx.lineTo(260, 190);
        ctx.moveTo(250, 200);
        ctx.lineTo(260, 210);
        ctx.stroke();
    }

    // 绘制可视化棋盘
    drawVisualBoard() {
        const canvas = document.getElementById('visual-board');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // 清空画布
        ctx.clearRect(0, 0, width, height);
        
        // 绘制棋盘背景
        ctx.fillStyle = '#e5c9a8';
        ctx.fillRect(0, 0, width, height);
        
        // 计算格子大小
        const cellWidth = (width - 40) / 8; // 留出边距
        const cellHeight = (height - 40) / 9;
        const offsetX = 20;
        const offsetY = 20;
        
        // 绘制网格线
        ctx.strokeStyle = '#8b5a2b';
        ctx.lineWidth = 1;
        
        // 横线
        for (let i = 0; i <= 9; i++) {
            const y = offsetY + i * cellHeight;
            ctx.beginPath();
            ctx.moveTo(offsetX, y);
            ctx.lineTo(width - offsetX, y);
            ctx.stroke();
        }
        
        // 竖线
        for (let i = 0; i <= 8; i++) {
            const x = offsetX + i * cellWidth;
            ctx.beginPath();
            ctx.moveTo(x, offsetY);
            ctx.lineTo(x, offsetY + 4 * cellHeight); // 上半部分
            ctx.stroke();
            
            ctx.beginPath();
            ctx.moveTo(x, offsetY + 5 * cellHeight);
            ctx.lineTo(x, offsetY + 9 * cellHeight); // 下半部分
            ctx.stroke();
        }
        
        // 九宫格斜线
        ctx.beginPath();
        ctx.moveTo(offsetX + 3 * cellWidth, offsetY);
        ctx.lineTo(offsetX + 5 * cellWidth, offsetY + 2 * cellHeight);
        ctx.moveTo(offsetX + 5 * cellWidth, offsetY);
        ctx.lineTo(offsetX + 3 * cellWidth, offsetY + 2 * cellHeight);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(offsetX + 3 * cellWidth, offsetY + 7 * cellHeight);
        ctx.lineTo(offsetX + 5 * cellWidth, offsetY + 9 * cellHeight);
        ctx.moveTo(offsetX + 5 * cellWidth, offsetY + 7 * cellHeight);
        ctx.lineTo(offsetX + 3 * cellWidth, offsetY + 9 * cellHeight);
        ctx.stroke();
        
        // 楚河汉界
        ctx.fillStyle = '#8b5a2b';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('楚 河', offsetX + 2 * cellWidth, offsetY + 4.5 * cellHeight);
        ctx.fillText('汉 界', offsetX + 6 * cellWidth, offsetY + 4.5 * cellHeight);
        
        // 棋子字符映射到中文名称
        const pieceNames = {
            'r': '車', 'n': '馬', 'b': '象', 'a': '士', 'k': '將', 'c': '砲', 'p': '卒',
            'R': '车', 'N': '马', 'B': '相', 'A': '仕', 'K': '帅', 'C': '炮', 'P': '兵'
        };
        
        // 绘制棋子
        const pieceRadius = Math.min(cellWidth, cellHeight) * 0.35;
        
        Object.entries(this.boardState).forEach(([posKey, pieceChar]) => {
            const [col, row] = posKey.split(',').map(Number);
            const x = offsetX + col * cellWidth;
            const y = offsetY + row * cellHeight;
            
            // 判断红黑方（大写=红方，小写=黑方）
            const isRed = pieceChar === pieceChar.toUpperCase();
            const pieceName = pieceNames[pieceChar] || '?';
            
            // 绘制棋子圆圈
            ctx.beginPath();
            ctx.arc(x, y, pieceRadius, 0, Math.PI * 2);
            ctx.fillStyle = isRed ? '#fff5f5' : '#f0f0f0';
            ctx.fill();
            ctx.strokeStyle = isRed ? '#dc2626' : '#1f2937';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // 如果是选中状态，添加高亮
            if (this.selectedSquare && this.selectedSquare.col === col && this.selectedSquare.row === row) {
                ctx.beginPath();
                ctx.arc(x, y, pieceRadius + 4, 0, Math.PI * 2);
                ctx.strokeStyle = '#3b82f6';
                ctx.lineWidth = 3;
                ctx.stroke();
            }
            
            // 绘制棋子文字
            ctx.fillStyle = isRed ? '#dc2626' : '#1f2937';
            ctx.font = `bold ${pieceRadius * 0.9}px "Microsoft YaHei", Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(pieceName, x, y);
        });
    }

    // 处理棋盘点击
    handleBoardClick(event) {
        if (!this.isPlayerTurn) {
            this.log('当前是AI回合，请等待', 'warning');
            return;
        }
        
        const canvas = event.target;
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // 计算点击的格子
        const cellWidth = (canvas.width - 40) / 8;
        const cellHeight = (canvas.height - 40) / 9;
        const offsetX = 20;
        const offsetY = 20;
        
        const col = Math.round((x - offsetX) / cellWidth);
        const row = Math.round((y - offsetY) / cellHeight);
        
        // 检查是否在棋盘范围内
        if (col < 0 || col > 8 || row < 0 || row > 9) return;
        
        const posKey = `${col},${row}`;
        
        if (!this.selectedSquare) {
            // 第一次点击：选择棋子（只能选红方）
            const piece = this.boardState[posKey];
            if (piece && piece === piece.toUpperCase()) { // 大写=红方
                this.selectedSquare = { col, row, key: posKey, piece };
                this.log(`选中棋子: ${piece} (${col}, ${row})`, 'info');
                this.drawVisualBoard();
            } else if (piece) {
                this.log('只能选择红方棋子', 'warning');
            }
        } else {
            // 第二次点击：移动棋子
            if (this.selectedSquare.key !== posKey) {
                const fromCol = this.selectedSquare.col;
                const fromRow = this.selectedSquare.row;
                const toCol = col;
                const toRow = row;
                
                // 转换为UCI格式走法
                const files = 'abcdefghi';
                // UCI排名：0=红方底线, 9=黑方底线
                // 我们的数组索引：0=黑方底线, 9=红方底线
                // 所以需要转换：array_row -> 9 - array_row
                const uciFromRow = 9 - fromRow;
                const uciToRow = 9 - toRow;
                const uciMove = `${files[fromCol]}${uciFromRow}${files[toCol]}${uciToRow}`;
                
                this.log(`玩家走法: ${this.selectedSquare.piece} (${fromCol},${fromRow}) -> (${toCol},${toRow})`, 'info');
                this.log(`UCI走法: ${uciMove}`, 'info');
                
                // 调用后端API执行玩家走法
                this.executePlayerMove(uciMove);
            } else {
                // 取消选择
                this.selectedSquare = null;
                this.drawVisualBoard();
            }
        }
    }

    // 执行玩家走法
    async executePlayerMove(uciMove) {
        try {
            const response = await fetch(`${this.apiBase}/player_move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ move: uciMove })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.log(`玩家走法已确认: ${uciMove}`, 'info');
                
                // 添加到走法历史
                this.moveHistory.push(uciMove);
                this.updateMoveList();
                
                // 更新FEN显示
                if (data.fen) {
                    document.getElementById('fen-display').value = data.fen;
                    this.log(`新FEN: ${data.fen}`, 'info');
                }
                
                // 更新回合状态
                this.isPlayerTurn = data.is_player_turn || false;
                this.updateGameStatus();
                
                // 清除选择状态
                this.selectedSquare = null;
                
                // 解析UCI走法并更新可视化棋盘（玩家走棋不需要机械臂）
                this.updateBoardFromUCIMove(uciMove, false);  // 玩家走法
                
                this.log('已轮到AI思考，请点击"获取AI走法"', 'info');
            } else {
                this.log(`走法失败: ${data.error}`, 'error');
                // 恢复选择状态
                this.drawVisualBoard();
            }
        } catch (error) {
            this.log(`执行走法错误: ${error.message}`, 'error');
            this.drawVisualBoard();
        }
    }

    // 更新游戏状态显示
    updateGameStatus() {
        const statusEl = document.getElementById('game-status');
        if (this.isPlayerTurn) {
            statusEl.textContent = '轮到红方（玩家）';
            statusEl.style.color = '#dc2626';
        } else {
            statusEl.textContent = '轮到黑方（AI）';
            statusEl.style.color = '#1f2937';
        }
    }

    // 初始化标准棋盘布局
    initStandardBoard() {
        this.log('🔧 initStandardBoard() 被调用', 'info');
        
        // 中国象棋初始布局
        const initial = {
            '0,0': 'r', '1,0': 'n', '2,0': 'b', '3,0': 'a', '4,0': 'k', '5,0': 'a', '6,0': 'b', '7,0': 'n', '8,0': 'r',
            '1,2': 'c', '7,2': 'c',
            '0,3': 'p', '2,3': 'p', '4,3': 'p', '6,3': 'p', '8,3': 'p',
            '0,6': 'P', '2,6': 'P', '4,6': 'P', '6,6': 'P', '8,6': 'P',
            '1,7': 'C', '7,7': 'C',
            '0,9': 'R', '1,9': 'N', '2,9': 'B', '3,9': 'A', '4,9': 'K', '5,9': 'A', '6,9': 'B', '7,9': 'N', '8,9': 'R'
        };
        
        this.log('⚙️ 设置 boardState 为标准布局...', 'info');
        this.boardState = {...initial};
        
        this.log('✅ 标准布局已设置，棋子数量: ' + Object.keys(this.boardState).length, 'info');
        this.log('📍 红炮位置: 1,7=' + this.boardState['1,7'] + ', 7,7=' + this.boardState['7,7'], 'info');
        this.log('📍 黑炮位置: 1,2=' + this.boardState['1,2'] + ', 7,2=' + this.boardState['7,2'], 'info');
        
        this.drawVisualBoard();
    }

    // 动画机械臂移动
    animateRobotMove(move) {
        // 简化动画
        this.drawRobotVisualization();
    }

    // 更新状态
    async updateStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            if (data.success) {
                this.currentState = data.state;
            }
        } catch (error) {
            // 静默失败
        }
    }

    // 日志输出
    log(message, type = 'info') {
        const logOutput = document.getElementById('log-output');
        const time = new Date().toLocaleTimeString('zh-CN');
        
        const entry = document.createElement('div');
        entry.className = `log-entry log-${type}`;
        entry.innerHTML = `<span class="log-time">[${time}]</span>${message}`;
        
        logOutput.appendChild(entry);
        logOutput.scrollTop = logOutput.scrollHeight;
        
        // 同时输出到控制台
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.simulation = new ChessSimulation();
    
    // 将函数暴露到全局作用域
    window.changeInputSource = () => window.simulation.changeInputSource();
    window.handleLocalImageUpload = (event) => window.simulation.handleLocalImageUpload(event);
});
