var AdminEditView = Backbone.View.extend({
    initialize: function(exerciseModel){
        this.template = _.template($("#admin-edit-view").html());
        this.exerciseModel = exerciseModel;
    },
    _getOrCreateEl: function(){
        if ($(".modal-parent").length === 0){
            $("body").append(
                "<div class='modal-parent'></div>"
            );
        }
        this.$el = $(".modal-parent");
    },
    render: function(){
        this._getOrCreateEl();
        var renderData = {
            "exercise": this.exerciseModel.toJSON(),
            "equipment": JSContext.equipment,
            "muscleGroups": JSContext.muscle_groups,
            "exerciseTypes": JSContext.exercise_types
        }
        console.log(renderData);
        this.$el.html(this.template(renderData));
        this.$("#myModal").modal();
    }
});
