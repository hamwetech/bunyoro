/*************************************************************************************/
// -->Template Name: Bootstrap Press Admin
// -->Author: Themedesigner
// -->Email: niravjoshi87@gmail.com
// -->File: google_map_init
/*************************************************************************************/

$(function() {


    //******************************************//
    // Markers
    //******************************************//

    var map_2;
    map_2 = new GMaps({
        div: '#map_2',
        lat: 2.3838612245263007,
        lng: 33.099402361834244,
        zoom: 7,
    });

    var base_url = window.location.origin;

    var request = $.ajax({
//      url: "{% url 'ajax_load_farmer_map' %}",
      url: base_url+"/coop/ajax/load-farmer/",
      method: "GET",
      dataType: "json"
    });

    request.done(function( msg ) {
       console.log(msg)
        for (var key in msg) {
            if (msg.hasOwnProperty(key)) {
                console.log(msg[key].gps)
                if(msg[key].gps != null){
                    gps = msg[key].gps
                    spl = gps.split(',')
                    if(spl.length > 1){
                        lat = spl[0]
                        lon = spl[1]

                        map_2.addMarker({
                            lat: lat,
                            lng: lon,
                            title: msg[key].name,
                            infoWindow: {
                                content: '<p>'+ msg[key].name +'</p>'
                            }
                        });
                    }
                }
             }
        }
    });

    request.fail(function( jqXHR, textStatus ) {
      alert( "Request failed: " + textStatus );

    });

//    map_2.addMarker({
//        lat: -12.043333,
//        lng: -77.03,
//        title: 'Lima',
//        details: {
//            database_id: 42,
//            author: 'HPNeo'
//        },
//        click: function(e) {
//            if (console.log)
//                console.log(e);
//            alert('You clicked in this marker');
//        }
//    });


});