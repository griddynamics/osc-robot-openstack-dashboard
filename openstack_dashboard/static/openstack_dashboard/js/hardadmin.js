var tableName;
var url;
var detailsUrl;
var actionUrl;
var details;

function addMessage(message) {
	var header = message.tags;
	header = header.substr(0, 1).toUpperCase() + header.substr(1);
    var message_html = $('<div class="message_box ' + 
    		message.tags + '"><h2>' + header + '</h2><p>' + message.message + '</p></div>');
    $("#ajax_errors").append(message_html);
    $("#ajax_errors").show();
}

function processResponse(response, table, settings) {
	$("#ajax_errors").html("");
	$.each(response.django_messages, function (i, item) {
         addMessage(item);
    });
	return 0;
}

function updateOverviewTable(tn, u, du, au){
    tableName=tn;
    url=u;
    detailsUrl=du;
    actionUrl=au;
    initUpdateAndSearch();
}

function initTable(tableName, url, detailsUrl, actionUrl){
    updateOverviewTable(tableName, url, detailsUrl, actionUrl);
}

function onBeforeUpdate(){
    details = [];
    $("#"+tableName+" tr").unbind();
    $(".power_on, .power_off, .power_reset, .remove_blade").unbind();
    $("#"+tableName+"_list tr").each(function(){
        if (this.hasAttribute("type")){
            details.push($(this.previousSibling).attr("id"));
        }
    });
}

function onAfterUpdate(){
    initOverviewTable(tableName, detailsUrl, actionUrl);
    $('#table_search').quicksearch("#"+tableName +" tbody tr");

    if (this.cachedData){
        for (var index=0; index<this.cachedData.length; index++){
            if (details.indexOf(this.cachedData[index].name+"_row") !== -1){
                $("#"+this.cachedData[index].name+"_row").attr("expanded", "true");
                $( "#detailsTemplate" ).tmpl(this.cachedData[index]).insertAfter("#"+this.cachedData[index].name+"_row")
            }
        }
    }

    updateProgressBar();
}
function initOverviewTable(tableName, detailsUrl, actionUrl){
    var rows = $("#"+tableName+" tbody tr");
    rows.mouseover(function(){

        $(this).addClass("even");
    });

    rows.mouseleave(function(){
        $(this).removeClass("even");
    });

    $(rows).each(function(){
        if (!$(this).attr("type")){
            $(this).click(function(){
                var row = $(this);
                if (row.attr("expanded")){
                    row.removeAttr("expanded");
                    $(this.nextSibling).remove();
                } else {
                    var url = detailsUrl + "?host=" + $(row.children("td")[0]).html();
                    $.get(url, function(data){
                            $( "#detailsTemplate" ).tmpl(data.details).insertAfter(row);
                            $(".fsmStatus").each(function(){
                                var elem = $(this);
                                if (elem.html().indexOf("nop") != -1){
                                    elem.css("display", "none");
                                }
                            });
                        },
                        "json");
                    row.attr("expanded", "true");
                }
            });
        }
    });

    $(".power-on, .power-off, .power-reset").each(function(){
        var link = $(this);
        link.click(function(){
            disableLinks(this);
            var elem = $(this);
            var action_data = "?type=" + elem.attr("action") + "&host=" + elem.attr("blade");
            $.ajax({
                type: 'GET',
                url: actionUrl + action_data
            });
            return false;
        });

        var powerState = $("#power-" + link.attr("blade")).html();
        if (powerState.indexOf("on") > -1){
            if (link.hasClass("power-on")){
                link.css("display", "none");
            } else{
                link.css("display", "inline");
            }
        }else{
            if (link.hasClass("power-on")){
                link.css("display", "inline");
            } else{
                link.css("display", "none");
            }
        }
    });

    $(".remove_blade").click(function(){
        if (confirm("Are you sure to remove blade?")){
            var elem = $(this);
            disableLinks(this);
            $("#"+tableName).ajaxTable('stop');
            var action_data = "?type=" + elem.attr("action") + "&host=" + elem.attr("blade");
            $.ajax({
                type: 'GET',
                url: actionUrl + action_data,
                success: function(data){
                    if (data) {
                        alert(data);
                    }
                    initUpdateAndSearch();
                }
            });
            $(this).html("Removing...");
        }
        return false;
    });
}

function disableLinks(link){
    var elems = $(link).parent().children();
    $(elems).attr("disabled", "true")
}

function removeDetailsRows(tableId){
    $("#" + tableId + " tr").each(function(){       
        if (this.hasAttribute("type")) {
            $(this).remove();
        }
        if ($(this).attr("expanded")){
            $(this).removeAttr("expanded");
        }
    });
}

function initAddBladeForm(){
    $("#blades input[type=radio]").click(function(){
        $("#blade_dn").val($(this).attr("dn"));
        $("#profile_dn").val($(this).attr("profileDn"));
    });

    var hasAvailable = false;
    var inputs = $("#blades input[type=radio]");
    var count = inputs.length;
    inputs.each(function(){
        if (this.id =! "auto_blade"){
            if ($(this).attr("disabled") == "true"){
                count--;
            }
        }
    });

    if (count == 0){
        $("#auto_blade").attr("disabled", "true");
        $("#add_btn").attr("disabled", "true");
    }
}

function initUpdateAndSearch(){
    $("#"+tableName).ajaxTable({'template': tableName+"Template",
                                    'url': url,
                                    'autoUpdate': true,
                                    'interval': 10000,
                                    'sortable': true,
                                    'beforeUpdate': onBeforeUpdate,
                                    'afterUpdate': onAfterUpdate,
                                    'afterSort': updateProgressBar,
                                    'processResponse': processResponse,
                                    'emptyTemplate': "emptyTemplate"});
        $('#table_search').quicksearch("#"+tableName +" tbody tr")
}

function updateProgressBar(){
    $(".fsm_progress_container").each(function(){
        var elem = $(this);
        if (elem.attr("value") == 100 || elem.attr("value") == ""){
            elem.css("display", "none");
            $(this.nextElementSibling).css("display", "none");
        }
    });
}