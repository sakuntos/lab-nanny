
function send_data_back(ref,number,state){
    var message =  [ref,number,state];
    connection.send(message);
    return state
}

function add_data_to_buffer(buffer, data){
    buffer.push(data);
    buffer.shift();
    return buffer;
}

function check_condition(single_dictionary,condition){
    //check if condition is fulfilled
    // a "true" condition means everything is all right
    // when the condition becomes "false", then there is an error
    var condition_status_min = 1,
        condition_status_max = 1,
        condition_status = 0;

    if("min_value" in condition){
       condition_status_min = (single_dictionary[condition.control]>condition.min_value);
    }
    if("max_value" in condition){
       condition_status_max = (single_dictionary[condition.control]<condition.max_value);
    }
    condition_status = (condition_status_min&condition_status_max);

    d3.select(mainObj[single_dictionary.user].lines[condition.control].node()
              .parentElement
              .parentElement
              .lastChild).classed("condition_error",!condition_status);
    return condition_status;
}

/////////////////////////////////
// MAIN CONSTRUCTOR:
////////////////////////////////

// For each ref input
for(var ref in mainObj){
  //Create connection text
  mainObj[ref].connection_text = d3.select(mainObj[ref].connection_text_area)
          .classed("error",true)
          .classed("connectionText",true)
          .text(ref+ ' connected');
  //Create the buttons specified in the "pins" property and add it to the
  //"buttons" list
  mainObj[ref].pins.forEach(function(pin){
  var my_button = makeButton(mainObj[ref].name,pin,"#toggle_buttons");
  mainObj[ref].buttons.push(my_button);
  });
  // Also, for each channel, associate to it some line data (initialized to a
  // default value) and plot it in a certain "graph_area".
  mainObj[ref].analogchannels.forEach(function(channel){
  var line_data = d3.range(n).map(function(){return 1;}); //Default values
  var my_line = displayGraphExample(mainObj[ref].graph_area,channel,mainObj[ref].representation[channel] || line);
  mainObj[ref].data[channel]  = line_data;
  mainObj[ref].lines[channel] = my_line;
  });

}

function update_lab_state(newData){
  // if no error found, update the channels specified in the lab's dict.
  //
  // if newData.error=true, update the channels using the -0.5 value, and
  // change the connection_text style to "error"
  var user = newData.user

  mainObj[user].conditions.forEach(function(condition){
     var condition_fulfilled = check_condition(newData,condition);
     if(!condition_fulfilled){
        //Perform required action:
        send_data_back(condition.control_user,
                       condition.target_channel,
                       +condition.target_value);
        //update buttons, if necessary
        var index = mainObj[condition.control_user].pins.indexOf(condition.target_channel);
        if(index> -1){
          var button = mainObj[condition.control_user].buttons[index];
          //button_toggle(button);
          button_value(button,condition.target_value);
        }
     }

  })

  if(!newData.error){
    var user = newData.user
    mainObj[user].analogchannels.forEach(function(channel){
      add_data_to_buffer(mainObj[user].data[channel],newData[channel]);
      redrawWithoutAnimation(mainObj[user].lines[channel],
                              mainObj[user].data[channel],
                             mainObj[user].representation[channel]||line);
        mainObj[user].lines[channel].classed('disconnected',false)
    })

    mainObj[user].connection_text.classed("error",false);
    }
  else{
    mainObj[user].analogchannels.forEach(function(channel){
      add_data_to_buffer(mainObj[user].data[channel],-0.5);
      redrawWithoutAnimation(mainObj[user].lines[channel],
                              mainObj[user].data[channel],
                             mainObj[user].representation[channel]||line);
        mainObj[newData.user].lines[channel].classed('disconnected',false)
    })

    mainObj[user].connection_text.classed("error",true);
  }
}

connection.onmessage = function(event) {
    var labs_dictionary = JSON.parse(event.data);
    //verbose output: // console.log(newMessage);
    Object.keys(labs_dictionary).forEach(function(labUUID){
    update_lab_state(labs_dictionary[labUUID]);
    })
 }

console.log(mainObj);
