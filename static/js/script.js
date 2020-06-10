function switchLight(hue_id) {
    var checked = jQuery('#switch_' + hue_id).prop('checked');
    jQuery.ajax({
        url: '/api/lights/' + hue_id,
        method: 'PUT',
        dataType: 'json',
        contentType: 'application/json',
        data: JSON.stringify({
            state: checked
        }),
        success: function(result, status, jqXHR) {
            appendAlert('success', 'light switched');
        },
        error: function(jqXHR, status, error) {
            appendAlert('danger', error);
        }
    });
}

function appendAlert(type, message) {
    jQuery('#alert-container').append(`
        <div class="alert alert-` + type + ` alert-dismissable fade show" role="alert">
            `+ message +`
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <spane aria-hidden="true">&times;</span>
            </button>
        </div>
    `);
}
