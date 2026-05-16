const { createApp } = Vue;

createApp({

delimiters: ['[[', ']]'],

data() {
    return {
        view: 'search',
        topicInput: '',
        loading: false,
        explored: null,
        selectedTopics: [],
        notes: null
    };
},

methods: {

async exploreTopic() {

    try {

        this.loading = true;

        const response = await fetch('/api/topics/explore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                topic: this.topicInput
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed');
        }

        this.explored = data;

        this.view = 'topics';

    } catch (err) {

        alert(err.message);

    } finally {

        this.loading = false;
    }
},

toggleTopic(topic) {

    if (this.selectedTopics.includes(topic)) {

        this.selectedTopics =
            this.selectedTopics.filter(t => t !== topic);

    } else {

        this.selectedTopics.push(topic);
    }
},

async generateNotes() {

    try {

        this.loading = true;

        const response = await fetch('/api/notes/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mainTopic: this.explored.mainTopic,
                selectedTopics: this.selectedTopics
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed');
        }

        this.notes = data;

        this.view = 'notes';

        this.$nextTick(() => {
            hljs.highlightAll();
        });

    } catch (err) {

        alert(err.message);

    } finally {

        this.loading = false;
    }
},

async downloadPDF() {

    const response = await fetch('/api/notes/download-pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(this.notes)
    });

    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');

    a.href = url;

    a.download = 'smart-notes.pdf';

    a.click();

    window.URL.revokeObjectURL(url);
}

}

}).mount('#app');
