document.addEventListener('DOMContentLoaded', () => {
    const quickJoinInput = document.getElementById('quick-join-code');
    const quickJoinBtn = document.getElementById('quick-join-btn');

    // Функция быстрого входа по коду
    function quickJoin() {
        if (!quickJoinInput) return;

        const code = quickJoinInput.value.trim().toUpperCase();

        if (code.length === 4) {
            // Перенаправляем на существующий url лобби
            window.location.href = `/quiz/lobby/${code}/`;
        } else {
            // Анимация ошибки и подсветка красным
            quickJoinInput.style.borderColor = '#FF006E';
            quickJoinInput.classList.add('shake');

            setTimeout(() => {
                quickJoinInput.classList.remove('shake');
                quickJoinInput.style.borderColor = '#4CC9F0'; // Возвращаем исходный цвет
            }, 500);
        }
    }

    // Слушатель клика на кнопку
    if (quickJoinBtn) {
        quickJoinBtn.addEventListener('click', quickJoin);
    }

    // Слушатель нажатия Enter в поле ввода
    if (quickJoinInput) {
        quickJoinInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // Запрещаем отправку формы, если она вдруг обернута в <form>
                quickJoin();
            }
        });
    }

    // Автообновление страницы каждые 15 секунд
    // (Необходимо для актуализации списка лобби в реальном времени)
    setTimeout(() => {
        window.location.reload();
    }, 15000);
});