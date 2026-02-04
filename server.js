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
const MODEL_ENDPOINT = "https://detect.roboflow.com/rebar-4y6jc-vrqiw/3"; 

app.use(express.static('public'));
app.use(express.json());

app.post('/analyze', upload.single('image'), async (req, res) => {
    if (!req.file) return res.status(400).send('No image uploaded.');

    const imagePath = req.file.path;
    
    // 【升级1】接收前端传来的动态参数
    // 如果前端没传，就用默认值 (15 和 50)
    const userConf = req.query.conf || 15;
    const userOverlap = req.query.overlap || 50;

    console.log(`1. 收到图片 | 参数: 置信度=${userConf}%, 重叠阈值=${userOverlap}%`);

    try {
        const form = new FormData();
        form.append("file", fs.createReadStream(imagePath));

        const response = await axios({
            method: "POST",
            url: MODEL_ENDPOINT,
            params: {
                api_key: API_KEY,
                // 使用动态参数
                confidence: userConf,  
                overlap: userOverlap
            },
            data: form,
            headers: {
                ...form.getHeaders()
            }
        });

        console.log("2. 识别成功！目标数:", response.data.predictions.length);

        fs.unlinkSync(imagePath);
        res.json(response.data);

    } catch (error) {
        if (fs.existsSync(imagePath)) fs.unlinkSync(imagePath);
        console.error("AI调用失败:", error.message);
        res.status(500).json({ error: "AI服务暂时不可用" });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`✅ V5.0 动态参数版已启动: http://localhost:${PORT}`);
});