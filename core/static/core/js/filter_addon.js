// Функции для сохранения и загрузки фильтров
function saveFilters() {
    const filters = {
        company: document.getElementById('company').value,
        year: document.getElementById('year').value,
        scenario: document.getElementById('scenario').value
    };
    localStorage.setItem('plReportFilters', JSON.stringify(filters));
}

function loadSavedFilters() {
    const saved = localStorage.getItem('plReportFilters');
    if (saved) {
        const filters = JSON.parse(saved);
        if (filters.company) document.getElementById('company').value = filters.company;
        if (filters.year) document.getElementById('year').value = filters.year;
        if (filters.scenario) document.getElementById('scenario').value = filters.scenario;
    }
}

// Автоматическая инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    // Загружаем сохраненные фильтры
    setTimeout(loadSavedFilters, 100);
    
    // Сохраняем при отправке формы
    const form = document.getElementById('filterForm');
    if (form) {
        form.addEventListener('submit', saveFilters);
    }
});