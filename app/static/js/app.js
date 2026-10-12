'use strict';

const $ = (id) => document.getElementById(id);
const fields = ['first_name', 'last_name', 'email', 'group'];
let page = 1;
let editingId = null;
let deletingStudent = null;
let saving = false;
let deleting = false;
let controller;
let searchTimer;
let toastTimer;

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const error = new Error(data.error || 'Не вдалося виконати запит.');
    error.fields = data.fields || {};
    throw error;
  }
  return data;
}

function showToast(message) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4000);
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderRows(students) {
  $('students-body').replaceChildren();
  for (const student of students) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    const identity = element('div', 'student-cell');
    const avatar = element('span', 'avatar', `${student.first_name[0]}${student.last_name[0]}`.toUpperCase());
    avatar.dataset.tone = student.id % 4;
    avatar.setAttribute('aria-hidden', 'true');
    const name = element('span', 'student-name', `${student.first_name} ${student.last_name}`);
    name.append(element('small', 'student-id', `ID ${String(student.id).padStart(4, '0')}`));
    identity.append(avatar, name);
    cell.append(identity);
    const group = document.createElement('td');
    group.append(element('span', 'group-badge', student.group));
    const actionsCell = document.createElement('td');
    const actions = element('div', 'row-actions');
    const edit = element('button', 'row-action', 'Редагувати');
    edit.setAttribute('aria-label', `Редагувати: ${student.first_name} ${student.last_name}`);
    edit.addEventListener('click', () => openForm(student));
    const remove = element('button', 'row-action delete', 'Видалити');
    remove.setAttribute('aria-label', `Видалити: ${student.first_name} ${student.last_name}`);
    remove.addEventListener('click', () => openDelete(student));
    actions.append(edit, remove);
    actionsCell.append(actions);
    row.append(cell, element('td', 'email-cell', student.email), group, actionsCell);
    $('students-body').append(row);
  }
}

async function loadStudents() {
  controller?.abort();
  const currentController = new AbortController();
  controller = currentController;
  const query = $('search').value.trim();
  const group = $('group-filter').value;
  const filtered = Boolean(query || group);
  $('reset-filters').hidden = !filtered;
  $('load-error').hidden = true;
  $('empty-state').hidden = true;
  $('loading').hidden = false;
  $('table-region').setAttribute('aria-busy', 'true');
  $('students-body').replaceChildren();
  $('previous-page').disabled = true;
  $('next-page').disabled = true;
  $('page-summary').textContent = 'Завантаження…';
  try {
    const params = new URLSearchParams({ q: query, group, page, per_page: 10 });
    const data = await api(`/api/students?${params}`, { signal: currentController.signal });
    const pages = Math.max(1, Math.ceil(data.total / data.per_page));
    if (page > pages) {
      page = pages;
      return loadStudents();
    }
    renderRows(data.items);
    $('student-count').textContent = data.all_count;
    $('group-count').textContent = data.groups.length;
    $('result-count').textContent = data.total;
    $('group-filter').replaceChildren(new Option('Усі групи', ''));
    for (const value of data.groups) $('group-filter').add(new Option(value, value));
    if (group && !data.groups.includes(group)) $('group-filter').add(new Option(group, group));
    $('group-filter').value = group;
    $('group-options').replaceChildren(...data.groups.map((value) => new Option(value, value)));
    $('empty-state').hidden = data.items.length !== 0;
    $('empty-title').textContent = filtered ? 'Студентів не знайдено' : 'Ваш реєстр починається тут';
    $('empty-description').textContent = filtered ? 'Спробуйте інший запит або скиньте фільтри.' : 'Додайте першого студента, щоб зберігати дані в одному місці.';
    $('empty-add').hidden = filtered;
    $('page-number').textContent = `${page} / ${pages}`;
    $('page-summary').textContent = data.total ? `Показано ${(page - 1) * data.per_page + 1}–${Math.min(page * data.per_page, data.total)} з ${data.total}` : 'Усього: 0 студентів';
    $('previous-page').disabled = page <= 1;
    $('next-page').disabled = page >= pages;
  } catch (error) {
    if (error.name === 'AbortError') return;
    $('load-error-message').textContent = error instanceof TypeError ? 'Не вдалося підключитися до сервера.' : error.message;
    $('load-error').hidden = false;
    $('page-summary').textContent = 'Не вдалося завантажити дані';
    $('student-count').textContent = '—';
    $('group-count').textContent = '—';
    $('result-count').textContent = '—';
  } finally {
    if (controller === currentController) {
      $('loading').hidden = true;
      $('table-region').setAttribute('aria-busy', 'false');
    }
  }
}

function clearErrors() {
  $('form-error').hidden = true;
  for (const field of fields) {
    $(`${field}-error`).textContent = '';
    $(field).removeAttribute('aria-invalid');
  }
}

function openForm(student = null) {
  editingId = student?.id ?? null;
  $('student-form').reset();
  clearErrors();
  $('form-title').textContent = student ? 'Редагувати студента' : 'Новий студент';
  for (const field of fields) $(field).value = student?.[field] ?? '';
  $('student-dialog').showModal();
  $('first_name').focus();
}

function closeForm() { if (!saving) $('student-dialog').close(); }

$('student-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (saving) return;
  clearErrors();
  const payload = Object.fromEntries(fields.map((field) => [field, $(field).value.trim()]));
  const invalidField = fields.find((field) => !payload[field] || !$(field).checkValidity());
  if (invalidField) {
    $(invalidField).setAttribute('aria-invalid', 'true');
    $(`${invalidField}-error`).textContent = invalidField === 'email' && payload.email ? 'Введіть коректну адресу email.' : 'Заповніть це поле.';
    $(invalidField).focus();
    return;
  }
  saving = true;
  $('save-student').disabled = true;
  $('save-student').textContent = 'Збереження…';
  try {
    await api(editingId ? `/api/students/${editingId}` : '/api/students', { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    $('student-dialog').close();
    showToast(editingId ? 'Дані студента оновлено' : 'Студента додано до реєстру');
    await loadStudents();
  } catch (error) {
    $('form-error').textContent = error instanceof TypeError ? 'Немає зв’язку із сервером. Спробуйте ще раз.' : error.message;
    $('form-error').hidden = false;
    for (const [field, message] of Object.entries(error.fields || {})) {
      if (fields.includes(field)) {
        $(`${field}-error`).textContent = message;
        $(field).setAttribute('aria-invalid', 'true');
      }
    }
    const invalid = fields.find((field) => $(field).getAttribute('aria-invalid') === 'true');
    if (invalid) $(invalid).focus();
  } finally {
    saving = false;
    $('save-student').disabled = false;
    $('save-student').textContent = 'Зберегти студента';
  }
});

function openDelete(student) {
  deletingStudent = student;
  $('delete-description').textContent = `${student.first_name} ${student.last_name} · ${student.group}`;
  $('delete-error').hidden = true;
  $('delete-dialog').showModal();
  $('cancel-delete').focus();
}

$('delete-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (deleting || !deletingStudent) return;
  deleting = true;
  $('confirm-delete').disabled = true;
  $('confirm-delete').textContent = 'Видалення…';
  try {
    await api(`/api/students/${deletingStudent.id}`, { method: 'DELETE' });
    $('delete-dialog').close();
    showToast('Студента видалено');
    await loadStudents();
  } catch (error) {
    $('delete-error').textContent = error instanceof TypeError ? 'Немає зв’язку із сервером. Спробуйте ще раз.' : error.message;
    $('delete-error').hidden = false;
  } finally {
    deleting = false;
    $('confirm-delete').disabled = false;
    $('confirm-delete').textContent = 'Видалити';
  }
});

for (const id of ['add-student', 'empty-add']) $(id).addEventListener('click', () => openForm());
for (const id of ['cancel-form', 'close-form']) $(id).addEventListener('click', closeForm);
$('student-dialog').addEventListener('cancel', (event) => { if (saving) event.preventDefault(); });
$('delete-dialog').addEventListener('cancel', (event) => { if (deleting) event.preventDefault(); });
$('cancel-delete').addEventListener('click', () => { if (!deleting) $('delete-dialog').close(); });
$('search').addEventListener('input', () => {
  controller?.abort();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { page = 1; loadStudents(); }, 250);
});
$('group-filter').addEventListener('change', () => { clearTimeout(searchTimer); page = 1; loadStudents(); });
$('reset-filters').addEventListener('click', () => {
  clearTimeout(searchTimer);
  $('search').value = '';
  $('group-filter').value = '';
  page = 1;
  loadStudents();
});
$('previous-page').addEventListener('click', () => { page -= 1; loadStudents(); });
$('next-page').addEventListener('click', () => { page += 1; loadStudents(); });
$('retry').addEventListener('click', loadStudents);
loadStudents();
