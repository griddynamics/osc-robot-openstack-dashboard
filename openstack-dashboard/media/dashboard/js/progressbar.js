/**
 * Copyright 2011 Grid Dynamics Consulting Services, Inc.  All rights reserved.
 *
 *    This software is provided to Cisco Systems, Inc. as "Supplier Materials"
 *    under the license terms governing Cisco's use of such Supplier Materials described
 *    in the Master Services Agreement between Grid Dynamics Consulting Services, Inc. and Cisco Systems, Inc.,
 *    as amended by Amendment #1.  If the parties are unable to agree upon the terms
 *    of the Amendment #1 by July 31, 2011, this license shall automatically terminate and
 *    all rights in the Supplier Materials shall revert to Grid Dynamics, unless Grid Dynamics specifically
 *    and otherwise agrees in writing.
*/

(function( $ ) {
    $.fn.progressBar = function(options) {
        var settings = {
            'hideFull'  : false,
            'hideEmpty' : false
        };

    this.each(function(){
        if (options) { 
            $.extend( settings, options );
        }

        var elem = $(this);
        var progress = elem.html();
        var hide = (settings.hideFull && progress == 100) || (settings.hideEmpty && progress == 0);
        if (!hide) {
            var containarClassName = "fsm_progress_container";
            if (!elem.hasClass(containarClassName))
            {
                elem.addClass(containarClassName);
                elem.html("<div class='fsm_progress' style='width:" + progress + "%;'>&nbsp;</div>");
                elem.after("<div class='fsm_progress_value' style='float:left;'>" + progress + "%</div><div style='clear:both;'></div>");
            }
        } else {
            elem.html("");
        }
    });
  };
})( jQuery );