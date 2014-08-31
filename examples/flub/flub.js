var Flub = React.createClass({
    getInitialState: function() {
        return {'bar': null};
    },

    componentWillMount: function() {
        var feed = new EventSource("/flub+events");
        feed.addEventListener("message", this.eventMsg, false);
    },

    eventMsg: function(msg) {
        var flubState = JSON.parse(msg.data);
        this.setState(flubState);
    },

    render: function() {
        return React.DOM.p({}, 'Hello, Flub! Current count: ' + this.state.bar);
    }
});

React.renderComponent(Flub(), document.body);
