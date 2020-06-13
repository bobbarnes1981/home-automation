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
    var date = new Date();
    jQuery('.toast-container').append(`
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" style="position: absolute; bottom: 10px; right:10px;">
            <div class="toast-header">
                <img src="" class="` + type + ` rounded mr-2" alt="" style="width:18px; height:18px; background-color: darkgray">
                <strong class="mr-auto">home-automation</strong>
                <small>` + date.getHours() + `:` + date.getMinutes() + `:` + date.getSeconds() + `</small>
                <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="toast-body">
                ` + message + `
            </div>
        </div> 
    `);
    var toast = jQuery('.toast').toast({
        animation: true,
        autohide: true,
        delay: 1000
    })
    toast.on('hidden.bs.toast', function(){
        jQuery(this).remove();
    });
    toast.toast('show');
}
