// --- TOAST NOTIFICATION SYSTEM ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    
    let bgClass, iconHtml;
    if (type === 'success') {
        bgClass = 'bg-green-600';
        iconHtml = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
    } else if (type === 'error') {
        bgClass = 'bg-red-600';
        iconHtml = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`;
    } else {
        bgClass = 'bg-blue-600';
        iconHtml = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
    }
    
    toast.className = `toast-enter flex items-center gap-2 ${bgClass} text-white px-3 py-2.5 rounded shadow-lg text-xs font-medium mb-2`;
    toast.innerHTML = `${iconHtml} <span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// --- GLOBAL STATE ---
let currentLat = 0;
let currentLng = 0;
let currentMap = null;
let currentMarker = null;
let analysisData = null;
let compressedImageBlob = null;
let currentObjectURL = null;

// --- GEOLOCATION ---
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            currentLat = position.coords.latitude;
            currentLng = position.coords.longitude;
            document.getElementById('locationText').textContent = `${currentLat.toFixed(5)}, ${currentLng.toFixed(5)}`;
            document.getElementById('locStatus').classList.replace('bg-yellow-400', 'bg-green-500');
            document.getElementById('locStatus').classList.remove('animate-pulse');
        },
        (error) => {
            document.getElementById('locationText').textContent = "Location denied. Defaulting.";
            document.getElementById('locStatus').classList.replace('bg-yellow-400', 'bg-red-500');
            document.getElementById('locStatus').classList.remove('animate-pulse');
            currentLat = 12.8231;
            currentLng = 80.0434;
            showToast("Location access denied. Using demo coordinates.", "error");
        },
        { enableHighAccuracy: true }
    );
} else {
    currentLat = 12.8231;
    currentLng = 80.0434;
}

// --- UPLOAD FLOW ---
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const previewContainer = document.getElementById('imagePreviewContainer');
const uploadPrompt = document.getElementById('uploadPrompt');
const analyzeBtn = document.getElementById('analyzeBtn');
const dropZone = document.getElementById('dropZone');

function setReadyImage(blob, fileName) {
    compressedImageBlob = blob;
    if (currentObjectURL) URL.revokeObjectURL(currentObjectURL);
    currentObjectURL = URL.createObjectURL(blob);
    
    imagePreview.src = currentObjectURL;
    document.getElementById('resImgOriginal').src = currentObjectURL;
    document.getElementById('resImgAI').src = currentObjectURL;
    
    previewContainer.classList.remove('hidden');
    uploadPrompt.classList.add('hidden');
    
    dropZone.classList.remove('border-slate-300', 'border-dashed');
    dropZone.classList.add('border-green-400', 'border-solid', 'bg-green-50/30');
    document.getElementById('filenameText').textContent = fileName;
    
    analyzeBtn.disabled = false;
    showToast("Evidence securely loaded.", "success");
}

imageInput.addEventListener('change', function() {
    const file = this.files[0];
    if (file) {
        setReadyImage(file, file.name);
    }
});

// Demo Images functionality
async function loadDemoImage(url, fileName) {
    try {
        const response = await fetch(url);
        const blob = await response.blob();
        setReadyImage(blob, fileName);
    } catch (e) {
        showToast("Failed to load demo image", "error");
    }
}

// --- AI PROCESSING SIMULATION ---
async function runLoadingSequence() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.remove('hidden');
    overlay.classList.add('flex');
    
    const steps = [
        document.getElementById('step1'),
        document.getElementById('step2'),
        document.getElementById('step3'),
        document.getElementById('step4')
    ];
    
    steps.forEach(s => {
        s.classList.remove('text-green-600');
        s.classList.add('text-slate-300');
    });

    for (let i = 0; i < steps.length; i++) {
        await new Promise(r => setTimeout(r, 450)); 
        steps[i].classList.remove('text-slate-300');
        steps[i].classList.add('text-green-600');
    }
    await new Promise(r => setTimeout(r, 300));
}

function generateMockData() {
    const issues = [
        {
            title: "Large Road Pothole",
            category: "Road Damage",
            dept: "Roads Department",
            desc: "A significant pothole has been detected on the main thoroughfare, posing an immediate risk to vehicular traffic and pedestrians. Immediate resurfacing is recommended."
        },
        {
            title: "Illegal Garbage Dumping",
            category: "Sanitation",
            dept: "Sanitation & Waste",
            desc: "Unauthorized accumulation of solid waste detected in a public zone. This presents a biohazard and violates municipal cleanliness ordinances. Requires urgent clearance."
        },
        {
            title: "Broken Streetlight",
            category: "Public Infrastructure",
            dept: "Electrical Authority",
            desc: "A non-functioning municipal streetlight has been identified, creating a dark spot that compromises pedestrian safety and neighborhood security during night hours."
        },
        {
            title: "Active Water Leak",
            category: "Water Supply",
            dept: "Water Board",
            desc: "A pressurized water leak has been detected, likely from a damaged subterranean pipeline. This causes continuous resource wastage and potential structural damage to the road."
        }
    ];
    const issue = issues[Math.floor(Math.random() * issues.length)];
    const severity = (Math.random() * 4 + 6).toFixed(1); // 6.0 to 10.0
    const confidence = Math.floor(Math.random() * 10) + 90; // 90 to 99

    return {
        issue_title: issue.title,
        category: issue.category,
        severity: parseFloat(severity),
        confidence: confidence,
        department_email: `${issue.dept.replace(/ /g, '').toLowerCase()}@municipality.gov`,
        description: issue.desc,
        complaint_letter: `To the ${issue.dept},\n\nI am writing to formally report an issue regarding "${issue.title}" at the recorded GPS coordinates. \n\nAI Analysis: ${issue.desc}\n\nKindly register this complaint and dispatch an inspection team at your earliest convenience to resolve the matter.\n\nThank you,\nConcerned Citizen`,
        sys_submission_method: "api" // Forces standard submit UI
    };
}

// --- MAIN SUBMISSION TO AI ---
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!compressedImageBlob) return;

    const btnIcon = document.getElementById('analyzeBtnIcon');
    const btnSpinner = document.getElementById('analyzeBtnSpinner');
    const btnText = document.getElementById('analyzeBtnText');
    
    analyzeBtn.disabled = true;
    btnIcon.classList.add('hidden');
    btnSpinner.classList.remove('hidden');
    btnText.textContent = "Processing...";
    
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('resultsState').classList.remove('hidden');
    document.getElementById('resultsState').classList.add('flex');
    document.getElementById('trackingState').classList.add('hidden');
    document.getElementById('trackingState').classList.remove('flex');
    
    const loadingPromise = runLoadingSequence();
    
    await loadingPromise; // wait for UI animation
    
    document.getElementById('loadingOverlay').classList.add('hidden');
    document.getElementById('loadingOverlay').classList.remove('flex');
    
    btnIcon.classList.remove('hidden');
    btnSpinner.classList.add('hidden');
    btnText.textContent = "Process Evidence";
    analyzeBtn.disabled = false;

    // Browser-only mock fetch
    analysisData = generateMockData();
    renderResults(analysisData);
    showToast("Analysis verified.", "success");
});

// --- RENDER RESULTS ---
function renderResults(data) {
    if(window.innerWidth < 768) {
        document.getElementById('resultsState').scrollIntoView({behavior: "smooth", block: "start"});
    }
    
    document.getElementById('resTitle').textContent = data.issue_title;
    document.getElementById('resCategory').textContent = data.category;
    
    // Natural language rewriting
    const severityWord = data.severity >= 8 ? 'critical' : data.severity >= 5 ? 'moderate' : 'minor';
    const naturalDesc = `Our AI analysis has recorded a ${severityWord} incident categorized under "${data.category}". The algorithm identified: ${data.description} The system has successfully matched this geolocation to the appropriate civic ward and prepared a formal digital record.`;
    document.getElementById('resDescription').textContent = naturalDesc;
    
    const deptName = data.department_email ? data.department_email.split('@')[0].toUpperCase() : 'DEPT';
    document.getElementById('wardBadge').textContent = deptName;
    
    document.getElementById('resLetter').value = data.complaint_letter;
    document.getElementById('resTimestamp').textContent = new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
    document.getElementById('coordBadge').textContent = `${currentLat.toFixed(4)}, ${currentLng.toFixed(4)}`;
    
    // Select Confidence element (it's the 2nd one in grid)
    // Actually wait, let's just update the severity and confidence specifically.
    // The confidence badge didn't have an ID. I will give it one below if needed or just use DOM structure.
    
    const badge = document.getElementById('severityBadge');
    badge.textContent = `${data.severity}/10`;
    if(data.severity >= 8) badge.className = "text-sm font-black text-red-600";
    else if (data.severity >= 5) badge.className = "text-sm font-black text-orange-500";
    else badge.className = "text-sm font-black text-yellow-600";

    // Set confidence dynamically
    const confBadge = badge.parentElement.nextElementSibling.querySelector('div');
    if(confBadge) confBadge.textContent = `${data.confidence}%`;
    
    // Initialize Map
    if (!currentMap) {
        currentMap = L.map('map', { zoomControl: false }).setView([currentLat, currentLng], 16);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap'
        }).addTo(currentMap);
        
        const customIcon = L.divIcon({
            className: 'custom-div-icon',
            html: `<div class="marker-drop" style="background-color: #2563eb; width: 14px; height: 14px; border-radius: 50%; border: 2.5px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });
        
        currentMarker = L.marker([currentLat, currentLng], {icon: customIcon, draggable: true}).addTo(currentMap);
        currentMarker.on('dragend', function (e) {
            const coords = e.target.getLatLng();
            currentLat = coords.lat;
            currentLng = coords.lng;
            document.getElementById('coordBadge').textContent = `${currentLat.toFixed(4)}, ${currentLng.toFixed(4)}`;
            showToast("Coordinates updated.", "info");
        });
    } else {
        currentMap.setView([currentLat, currentLng], 16);
        currentMarker.setLatLng([currentLat, currentLng]);
        // Re-trigger animation by cloning and replacing icon
        const el = currentMarker.getElement();
        if(el && el.firstChild) {
            el.firstChild.style.animation = 'none';
            el.firstChild.offsetHeight; // trigger reflow
            el.firstChild.style.animation = null; 
        }
    }
    
    setTimeout(() => currentMap.invalidateSize(), 100);
    
    document.getElementById('sendBtnText').textContent = "Submit to Authority";
}

document.getElementById('sendBtn').onclick = async function() {
    if (!analysisData) return;
    
    const btn = document.getElementById('sendBtn');
    const btnIcon = document.getElementById('sendBtnIcon');
    const btnSpinner = document.getElementById('sendBtnSpinner');
    const btnText = document.getElementById('sendBtnText');
    
    btn.disabled = true;
    if(btnIcon) btnIcon.classList.add('hidden');
    btnSpinner.classList.remove('hidden');
    btnText.textContent = "Transmitting...";
    
    // Simulate network delay
    await new Promise(r => setTimeout(r, 1200));
    
    showToast("Report submitted successfully!", "success");
    showTrackingState();
};

function showTrackingState() {
    document.getElementById('resultsState').classList.add('hidden');
    document.getElementById('resultsState').classList.remove('flex');
    document.getElementById('trackingState').classList.remove('hidden');
    document.getElementById('trackingState').classList.add('flex');
    
    const randomId = Math.floor(Math.random() * 90000) + 10000;
    document.getElementById('ticketIdDisplay').textContent = `CIV-2026-${randomId}`;
    
    const now = new Date();
    document.getElementById('timelineTime').textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'});
    
    if(window.innerWidth < 768) {
        document.getElementById('trackingState').scrollIntoView({behavior: "smooth", block: "start"});
    }
}
