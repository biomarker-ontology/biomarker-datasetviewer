import React, { Component } from "react";
import Paper from '@material-ui/core/Paper';
import InputBase from '@material-ui/core/InputBase';


class Searchbox extends Component {
  
  render() {

    var selectorLines = [];
    for (var key in this.props.initObj["search_options"]){
        selectorLines.push(<option value={key}>{this.props.initObj["search_options"][key]}</option>);
    }
    return (
        <div>
            <div className="search_label">Search</div>
            <div className="search_options"> 
                <select id="searchtype" className="form-select" style={{width:"100%"}} >{selectorLines}</select>
            </div>
            <div className="search_paper_wrapper"> 
                <Paper component="form" elevation="0" className="searchbox_paper">
                    <InputBase id="query" className="searchbox_input"  
                        placeholder={this.props.placeholder} 
                        defaultValue={this.props.defaultvalue}
                        inputProps={{ 'aria-label': '', 
                        'style': {fontSize: "14px", color:"#777"}}}
                        onKeyPress={this.props.onKeyPress}
                    />          
                <div onClick={this.props.onSearch} className="material-icons search_icon">search</div>
                </Paper>
            </div>
        </div>
    );
  }
}

export default Searchbox;
