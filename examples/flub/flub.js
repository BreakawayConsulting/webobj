var Flub = React.createClass({
    render: function() {
        return React.DOM.p({}, 'Hello, Flub!');
    }
});

React.renderComponent(Flub(), document.body);
