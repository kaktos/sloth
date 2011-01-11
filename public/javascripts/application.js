/*
 copy from rails.js
*/

$(function(){
     $.fn.extend({
        /**
         * Triggers a custom event on an element and returns the event result
         * this is used to get around not being able to ensure callbacks are placed
         * at the end of the chain.
         *
         * TODO: deprecate with jQuery 1.4.2 release, in favor of subscribing to our
         *       own events and placing ourselves at the end of the chain.
         */
        triggerAndReturn: function (name, data) {
            var event = new $.Event(name);
            this.trigger(event, data);

            return event.result !== false;
        }
       });
       
       
       
     /**
     *  confirmation handler
     */

    $('body').delegate('a[data-confirm], button[data-confirm], input[data-confirm]', 'click.rails', function () {
        var el = $(this);
        if (el.triggerAndReturn('confirm')) {
            if (!confirm(el.attr('data-confirm'))) {
                return false;
            }
        }
    });
    
     
  $('a[data-method]:not([data-remote])').live('click.rails', function (e){
        var link = $(this),
        href = link.attr('href'),
        method = link.attr('data-method'),
        form = $('<form method="post" action="'+href+'"></form>'),
        metadata_input = '<input name="_method" value="'+method+'" type="hidden" />';
  	form.hide().append(metadata_input).appendTo('body');
  	e.preventDefault();
        form.submit();
   });

 

})
