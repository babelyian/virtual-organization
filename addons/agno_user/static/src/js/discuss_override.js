odoo.define('agno_user.discuss_override', function (require) {
    "use strict";

    var Message = require('mail.model.Message');

    // Override the message rendering to preserve line breaks
    Message.include({
        getBody: function () {
            var body = this._super.apply(this, arguments);
            if (body && typeof body === 'string') {
                // Preserve line breaks in RTL text
                body = body.replace(/\n/g, '<br/>');
                // Ensure proper BiDi
                body = '<div style="white-space: pre-wrap; unicode-bidi: plaintext;">' + body + '</div>';
            }
            return body;
        },
    });
});