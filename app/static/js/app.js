/* =====================================================================
   Общие сценарии интерфейса (без сторонних библиотек).

   Модальные окна:
     <button data-open="modal-id">          — открыть окно
     <button data-close>                     — закрыть ближайшее окно
     клик по затемнению или Esc              — закрыть
     App.openModal(id) / App.closeModal()    — из кода страницы

   Подтверждение действия:
     <form data-confirm="Удалить тест?">     — спросит перед отправкой

   Поиск по списку:
     <input data-filter="#list-id">          — скрывает элементы списка
     элементы списка помечаются атрибутом data-search="текст для поиска"
   ===================================================================== */
(function () {
    'use strict';

    function openModal(id) {
        var el = document.getElementById(id);
        if (!el) return null;
        el.classList.add('is-open');
        document.body.classList.add('modal-open');
        var first = el.querySelector('input:not([type=hidden]), select, textarea');
        if (first) setTimeout(function () { first.focus(); }, 30);
        return el;
    }

    function closeModal(el) {
        var list = el ? [el] : document.querySelectorAll('.modal.is-open');
        Array.prototype.forEach.call(list, function (m) { m.classList.remove('is-open'); });
        if (!document.querySelector('.modal.is-open')) {
            document.body.classList.remove('modal-open');
        }
    }

    document.addEventListener('click', function (e) {
        var opener = e.target.closest('[data-open]');
        if (opener) {
            e.preventDefault();
            openModal(opener.getAttribute('data-open'));
            return;
        }
        var closer = e.target.closest('[data-close]');
        if (closer) {
            e.preventDefault();
            closeModal(closer.closest('.modal'));
            return;
        }
        if (e.target.classList && e.target.classList.contains('modal')) {
            closeModal(e.target);
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeModal();
    });

    document.addEventListener('submit', function (e) {
        var msg = e.target.getAttribute && e.target.getAttribute('data-confirm');
        if (msg && !window.confirm(msg)) e.preventDefault();
    });

    document.addEventListener('input', function (e) {
        var sel = e.target.getAttribute && e.target.getAttribute('data-filter');
        if (!sel) return;
        var q = e.target.value.trim().toLowerCase();
        var box = document.querySelector(sel);
        if (!box) return;
        var shown = 0;
        box.querySelectorAll('[data-search]').forEach(function (row) {
            var ok = !q || row.getAttribute('data-search').toLowerCase().indexOf(q) !== -1;
            row.hidden = !ok;
            if (ok) shown++;
        });
        var empty = document.querySelector(sel + '-empty');
        if (empty) empty.hidden = shown !== 0;
    });

    window.App = { openModal: openModal, closeModal: closeModal };
})();
