// Module Imports
global.jQuery = require('jquery');
const $ = jQuery;
const Popper = require('popper.js');
const bootstrap = require('bootstrap');
const selectpicker = require('bootstrap-select');
const animsition = require('animsition');
const ClipboardJS = require('clipboard');

$('#location').selectpicker({
  liveSearchNormalize: true,
  style: '',
  styleBase: 'form-control',
  iconBase: '',
  tickIcon: 'remixicon-check-line',
});

$('#query_type').selectpicker({
  liveSearchNormalize: true,
  style: '',
  styleBase: 'form-control',
  iconBase: '',
  tickIcon: 'remixicon-check-line',
});

$(document).ready(() => {
  $('#hg-results').hide();
  $('#hg-ratelimit-query').modal('hide');
  $('.animsition').animsition({
    inClass: 'fade-in',
    outClass: 'fade-out',
    inDuration: 800,
    outDuration: 800,
    transition: (url) => { window.location.href = url; },
  });

  $('#hg-form').animsition('in');
});

const resetResults = () => {
  const queryLocation = $('#location');
  const queryType = $('#query_type');
  const queryTarget = $('#query_target');
  const resultsContainer = $('#hg-results');
  const formContainer = $('#hg-form');
  const resultsAccordion = $('#hg-accordion');
  queryLocation.selectpicker('deselectAll');
  queryType.selectpicker('val', '');
  queryTarget.val('');
  resultsContainer.animsition('out', formContainer, '#');
  resultsContainer.hide();
  formContainer.show();
  formContainer.animsition('in');
  resultsAccordion.empty();
};

const queryApp = (queryType, queryTypeName, locationList, queryTarget) => {
  const resultsTitle = `${queryTypeName} Query for ${queryTarget}`;

  $('#hg-results-title').html(resultsTitle);

  $('#hg-submit-icon').empty().removeClass('hg-loading').html('<i class="remixicon-search-line"></i>');

  $.each(locationList, (n, loc) => {
    const locationName = $(`#${loc}`).data('display-name');
    const networkName = $(`#${loc}`).data('netname');

    const contentHtml = `
    <div class="card" id="${loc}-output">
      <div class="card-header bg-light text-dark" id="${loc}-heading">
        <div class="float-right hg-status-container" id="${loc}-status-container">
          <button type="button" class="float-right btn btn-light btn-lg hg-menu-btn hg-status-btn" 
            data-location="${loc}" id="${loc}-status-btn" disabled>
          </button>
        </div>
        <button type="button" class="float-right btn btn-light btn-lg hg-menu-btn hg-copy-btn" 
          data-clipboard-target="#${loc}-text" id="${loc}-copy-btn" disabled>
          <i class="remixicon-file-copy-line hg-menu-icon hg-copy hg-copy-icon"></i>
        </button>
        <h2 class="mb-0" id="${loc}-heading-container">
          <button class="btn btn-link text-secondary" type="button" data-toggle="collapse" 
            data-target="#${loc}-content" aria-expanded="true" aria-controls="${loc}-content"
            id="${loc}-heading-text">
          </button>
        </h2>
      </div>
      <div class="collapse" id="${loc}-content" aria-labelledby="${loc}-heading" data-parent="#hg-accordion">
        <div class="card-body" id="${loc}-text">
        </div>
      </div>
    </div>
    `;

    if ($(`#${loc}-output`).length) {
      $(`#${loc}-output`).replaceWith(contentHtml);
    } else {
      $('#hg-accordion').append(contentHtml);
    }
    const iconLoading = `<i id="${loc}-spinner" class="hg-menu-icon hg-status-icon remixicon-loader-4-line text-secondary"></i>`;

    $(`#${loc}-heading-text`).text(locationName);
    $(`#${loc}-status-container`)
      .addClass('hg-loading')
      .find('.hg-status-btn')
      .empty()
      .html(iconLoading);

    const generateError = (errorClass, locError, text) => {
      const iconError = '<i class="hg-menu-icon hg-status-icon remixicon-alert-line"></i>';
      $(`#${locError}-heading`).removeClass('text-secondary bg-light').addClass(`bg-${errorClass}`);
      $(`#${locError}-heading-text`).removeClass('text-secondary');
      $(`#${locError}-heading`).find('.hg-menu-btn').removeClass('btn-light').addClass(`btn-${errorClass}`);
      $(`#${locError}-status-container`)
        .removeClass('hg-loading')
        .find('.hg-status-btn')
        .empty()
        .html(iconError);
      $(`#${locError}-text`).html(text);
    }

    $.ajax({
      url: '/lg',
      type: 'POST',
      data: JSON.stringify({
        location: loc,
        query_type: queryType,
        target: queryTarget,
      }),
      contentType: 'application/json; charset=utf-8',
      context: document.body,
      async: true,
      timeout: 15000,
    })
      .done((data, textStatus, jqXHR) => {
        const displayHtml = `<pre>${jqXHR.responseText}</pre>`;
        const iconSuccess = '<i class="hg-menu-icon hg-status-icon remixicon-check-line"></i>';
        $(`#${loc}-heading`).removeClass('text-secondary bg-light').addClass('bg-primary');
        $(`#${loc}-heading-text`).removeClass('text-secondary');
        $(`#${loc}-heading`).find('.hg-menu-btn').removeClass('btn-light').addClass('btn-primary');
        $(`#${loc}-status-container`)
          .removeClass('hg-loading')
          .find('.hg-status-btn')
          .empty()
          .html(iconSuccess);
        $(`#${loc}-text`).empty().html(displayHtml);
      })
      .fail((jqXHR, textStatus, errorThrown) => {
        const codesDanger = [401, 415, 500, 501, 503];
        const codesWarning = [405];
        if (textStatus === 'timeout') {
          const displayText = 'Request timed out.';
          const displayHtml = `<div class="alert alert-warning" role="alert">${displayText}</div>`;
          const iconTimeout = '<i class="remixicon-time-line"></i>';
          $(`#${loc}-heading`).removeClass('text-secondary bg-light').addClass('bg-warning');
          $(`#${loc}-heading-text`).removeClass('text-secondary');
          $(`#${loc}-status-container`).empty().removeClass('hg-loading').html(iconTimeout);
          $(`#${loc}-heading`).find('.hg-menu-btn').removeClass('btn-light').addClass('btn-warning');
          $(`#${loc}-text`).html(displayHtml);
        } else if (codesDanger.includes(jqXHR.status)) {
          generateError('danger', loc, jqXHR.responseText);
        } else if (codesWarning.includes(jqXHR.status)) {
          generateError('warning', loc, jqXHR.responseText);
        } else if (jqXHR.status === 429) {
          resetResults();
          $('#hg-ratelimit-query').modal('show');
        }
      })
      .always(() => {
        $(`#${loc}-status-btn`).removeAttr('disabled');
        $(`#${loc}-copy-btn`).removeAttr('disabled');
      });
    $(`#${locationList[0]}-content`).collapse('show');
  });
};

// Submit Form Action
$('#lgForm').submit((event) => {
  event.preventDefault();
  $('#hg-submit-icon').empty().html('<i class="remixicon-loader-4-line"></i>').addClass('hg-loading');
  const queryType = $('#query_type').val();
  const queryTypeTitle = $(`#${queryType}`).data('display-name');
  const queryLocation = $('#location').val();
  const queryTarget = $('#query_target').val();

  queryApp(queryType, queryTypeTitle, queryLocation, queryTarget);
  $('#hg-form').animsition('out', $('#hg-results'), '#');
  $('#hg-form').hide();
  $('#hg-results').show();
  $('#hg-results').animsition('in');
  $('#hg-submit-spinner').remove();
});

$('#hg-back').click(() => {
  resetResults();
});

const clipboard = new ClipboardJS('.hg-copy-btn');
clipboard.on('success', (e) => {
  $(e.trigger).find('.hg-copy-icon').removeClass('remixicon-file-copy-line').addClass('remixicon-task-line');
  e.clearSelection();
  setTimeout(() => {
    $(e.trigger).find('.hg-copy-icon').removeClass('remixicon-task-line').addClass('remixicon-file-copy-line');
  }, 800);
});
clipboard.on('error', (e) => {
  console.log(e);
});

$('#hg-accordion').on('mouseenter', '.hg-status-btn', (e) => {
  $(e.currentTarget)
    .find('.hg-status-icon')
    .addClass('remixicon-repeat-line');
});

$('#hg-accordion').on('mouseleave', '.hg-status-btn', (e) => {
  $(e.currentTarget)
    .find('.hg-status-icon')
    .removeClass('remixicon-repeat-line');
});

$('#hg-accordion').on('click', '.hg-status-btn', (e) => {
  const thisLocation = $(e.currentTarget).data('location');
  console.log(`Refreshing ${thisLocation}`);
  const queryType = $('#query_type').val();
  const queryTypeTitle = $(`#${queryType}`).data('display-name');
  const queryTarget = $('#query_target').val();


  queryApp(queryType, queryTypeTitle, [thisLocation,], queryTarget);
});

$('#hg-ratelimit-query').on('shown.bs.modal', () => {
  $('#hg-ratelimit-query').trigger('focus');
});

$('#hg-ratelimit-query').find('btn').on('click', () => {
  $('#hg-ratelimit-query').modal('hide');
});
