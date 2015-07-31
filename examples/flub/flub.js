var Flub = React.createClass({
    getInitialState: function() {
        return {'bar': null};
    },

    eventMsg: function(msg) {
        var flubState = JSON.parse(msg.data);
        this.setState(flubState);
    },

    flubGet: function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "/flub/json_get", false);
        xhr.send();
        console.log(xhr.status, xhr.responseText);
    },

    flubPost: function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/flub/json_post", false);
        xhr.send('{"example": "POST"}');
        console.log(xhr.status, xhr.responseText);
    },

    flubPut: function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open("PUT", "/flub/json_put", false);
        xhr.send('{"example": "PUT"}');
        console.log(xhr.status, xhr.responseText);
    },

    render: function() {
        return React.DOM.div({},
                             React.DOM.p({}, 'Hello, Flub! Current count: ' + this.state.bar),
                             React.DOM.button({'onClick': this.flubGet}, 'Get!'),
                             React.DOM.button({'onClick': this.flubPost}, 'Post!'),
                             React.DOM.button({'onClick': this.flubPut}, 'Put!')
                            );
    }
});

React.renderComponent(Flub(), document.body);
