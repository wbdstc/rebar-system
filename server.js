const express = require('express');
const multer = require('multer');
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');
const path = require('path');

const app = express();
const upload = multer({ dest: 'uploads/' });

// --- 配置区域 ---
const API_KEY = "TJD6y13Dru57zUSoA0D1";

// 【关键升级】定义两个模型的大脑地址
const MODELS = {
    // 1. 间距检测模型 (侧面网格) - 之前的 V8.0
    'spacing': "https://detect.roboflow.com/rebar-4y6jc-vrqiw/3",

    // 2. 计数/直径模型 (端面圆头) - V9.0
    'counting': "https://detect.roboflow.com/rebar-9zzhq-zm30m/1"
};

app.use(express.static('public', { index: false }));
app.use(express.json());

// 默认首页重定向
app.get('/', (req, res) => {
    res.redirect('/portal.html');
});

app.post('/analyze', upload.single('image'), async (req, res) => {
    if (!req.file) return res.status(400).send('No image uploaded.');

    const imagePath = req.file.path;

    // 获取前端传来的模式：'spacing' 或 'counting'
    const mode = req.query.mode || 'spacing';
    const userConf = req.query.conf || 40;
    const userOverlap = req.query.overlap || 40;

    // 根据模式选择对应的模型 URL
    const targetUrl = MODELS[mode];

    console.log(`收到请求 | 模式: ${mode} | 模型: ${targetUrl}`);

    try {
        const form = new FormData();
        form.append("file", fs.createReadStream(imagePath));

        const response = await axios({
            method: "POST",
            url: targetUrl,
            params: {
                api_key: API_KEY,
                confidence: userConf,
                overlap: userOverlap
            },
            data: form,
            headers: { ...form.getHeaders() }
        });

        console.log("识别成功，目标数:", response.data.predictions.length);
        fs.unlinkSync(imagePath);
        res.json(response.data);

    } catch (error) {
        if (fs.existsSync(imagePath)) fs.unlinkSync(imagePath);
        console.error("模型调用失败:", error.message);
        res.status(500).json({ error: "模型调用失败" });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`✅ V10.0 双核旗舰版已启动: http://localhost:${PORT}`);
});